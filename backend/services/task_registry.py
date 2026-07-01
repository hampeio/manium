from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Literal
from uuid import uuid4


TaskState = Literal["queued", "running", "paused", "succeeded", "failed"]


@dataclass
class TaskRecord:
    task_id: str
    state: TaskState = "queued"
    logs: list[str] = field(default_factory=list)
    result: dict[str, object] | None = None
    partial_result: dict[str, object] | None = None
    error: str | None = None
    project_dir: str | None = None
    pause_requested: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class TaskRegistry:
    """Small in-memory task store for local desktop generation jobs."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = Lock()

    def create(self, project_dir: str | None = None) -> TaskRecord:
        task = TaskRecord(task_id=uuid4().hex, project_dir=project_dir)
        with self._lock:
            self._tasks[task.task_id] = task
        self.log(task.task_id, "任务已进入队列。")
        return task

    def start(self, task_id: str) -> None:
        self._update(task_id, state="running")
        self.log(task_id, "任务已开始。")

    def complete(self, task_id: str, result: dict[str, object]) -> None:
        self._update(task_id, state="succeeded", result=result)
        self.log(task_id, "任务已完成。")

    def update_partial(self, task_id: str, partial: dict[str, object]) -> None:
        with self._lock:
            task = self._tasks[task_id]
            current = dict(task.partial_result or {})
            current.update(partial)
            task.partial_result = current
            task.updated_at = datetime.now().isoformat(timespec="seconds")

    def fail(self, task_id: str, error: str) -> None:
        self._update(task_id, state="failed", error=error)
        self.log(task_id, f"任务失败：{error}")

    def pause(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state not in {"queued", "running", "paused"}:
                return False
            task.pause_requested = True
            task.state = "paused"
            task.updated_at = datetime.now().isoformat(timespec="seconds")
        self.log(task_id, "已请求暂停任务。")
        return True

    def resume(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state != "paused":
                return False
            task.pause_requested = False
            task.state = "running"
            task.updated_at = datetime.now().isoformat(timespec="seconds")
        self.log(task_id, "任务已继续。")
        return True

    def is_pause_requested(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            return bool(task and task.pause_requested)

    def log(self, task_id: str, message: str) -> None:
        with self._lock:
            task = self._tasks[task_id]
            timestamp = datetime.now().strftime("%H:%M:%S")
            task.logs.append(f"[{timestamp}] {message}")
            task.updated_at = datetime.now().isoformat(timespec="seconds")

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def to_dict(self, task_id: str) -> dict[str, object] | None:
        task = self.get(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "state": task.state,
            "logs": task.logs,
            "result": task.result,
            "partial_result": task.partial_result,
            "error": task.error,
            "project_dir": task.project_dir,
            "pause_requested": task.pause_requested,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    def _update(self, task_id: str, **changes: object) -> None:
        with self._lock:
            task = self._tasks[task_id]
            for key, value in changes.items():
                setattr(task, key, value)
            task.updated_at = datetime.now().isoformat(timespec="seconds")
