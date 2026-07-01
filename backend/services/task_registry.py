import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import uuid4


TaskState = Literal["queued", "running", "paused", "succeeded", "failed", "stalled", "interrupted"]
TERMINAL_STATES = {"succeeded", "failed", "stalled", "interrupted"}


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
    progress_percent: int = 0
    current_stage: str = "queued"
    current_step: str = "排队等待生成"
    completed_steps: list[str] = field(default_factory=list)
    remaining_steps: list[str] = field(default_factory=lambda: ["分析提示词", "生成分镜", "生成片段", "渲染视频", "生成音频", "完成"])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: str | None = None
    heartbeat_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    finished_at: str | None = None


class TaskRegistry:
    """Persistent local task store with heartbeat and stalled-task detection."""

    def __init__(self, projects_root: Path | None = None, stall_timeout_seconds: int = 600) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = Lock()
        self.projects_root = Path(projects_root or "generated_projects")
        self.stall_timeout_seconds = stall_timeout_seconds
        self._load_interrupted_tasks()

    def create(self, project_dir: str | None = None) -> TaskRecord:
        task = TaskRecord(task_id=uuid4().hex, project_dir=project_dir)
        with self._lock:
            self._tasks[task.task_id] = task
            self._persist(task)
        self.log(task.task_id, "任务已进入队列。")
        return task

    def start(self, task_id: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self._update(task_id, state="running", started_at=now, current_stage="preparing", current_step="准备素材中", progress_percent=5)
        self.log(task_id, "任务已开始。")

    def complete(self, task_id: str, result: dict[str, object]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self._update(
            task_id,
            state="succeeded",
            result=result,
            progress_percent=100,
            current_stage="completed",
            current_step="生成完成",
            remaining_steps=[],
            finished_at=now,
        )
        self.log(task_id, "任务已完成。")

    def update_partial(self, task_id: str, partial: dict[str, object]) -> None:
        with self._lock:
            task = self._tasks[task_id]
            current = dict(task.partial_result or {})
            current.update(partial)
            task.partial_result = current
            self._touch(task)
            self._persist(task)

    def fail(self, task_id: str, error: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self._update(task_id, state="failed", error=error, current_stage="failed", current_step="生成失败", finished_at=now)
        self.log(task_id, f"任务失败：{error}")

    def pause(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state not in {"queued", "running", "paused"}:
                return False
            task.pause_requested = True
            task.state = "paused"
            task.current_step = "已暂停"
            self._touch(task)
            self._persist(task)
        self.log(task_id, "已请求暂停任务。")
        return True

    def resume(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state != "paused":
                return False
            task.pause_requested = False
            task.state = "running"
            task.current_step = "继续生成"
            self._touch(task)
            self._persist(task)
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
            task.logs = task.logs[-500:]
            self._apply_progress(task, message)
            self._touch(task)
            self._persist(task)

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                self._supervise(task)
            return task

    def to_dict(self, task_id: str) -> dict[str, object] | None:
        task = self.get(task_id)
        return asdict(task) if task else None

    def list_dicts(self) -> list[dict[str, object]]:
        with self._lock:
            for task in self._tasks.values():
                self._supervise(task)
            return [asdict(task) for task in sorted(self._tasks.values(), key=lambda item: item.updated_at, reverse=True)]

    def _update(self, task_id: str, **changes: object) -> None:
        with self._lock:
            task = self._tasks[task_id]
            for key, value in changes.items():
                setattr(task, key, value)
            self._touch(task)
            self._persist(task)

    def _touch(self, task: TaskRecord) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        task.updated_at = now
        task.heartbeat_at = now

    def _supervise(self, task: TaskRecord) -> None:
        if task.state != "running":
            return
        heartbeat = datetime.fromisoformat(task.heartbeat_at)
        age = (datetime.now() - heartbeat).total_seconds()
        if age <= self.stall_timeout_seconds:
            return
        task.state = "stalled"
        task.error = f"后台任务超过 {self.stall_timeout_seconds} 秒没有心跳，可能已卡死或子进程中断。"
        task.current_stage = "stalled"
        task.current_step = "任务卡住"
        task.finished_at = datetime.now().isoformat(timespec="seconds")
        task.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 任务卡死：{task.error}")
        self._persist(task)

    def _apply_progress(self, task: TaskRecord, message: str) -> None:
        stage, step, percent = task.current_stage, message, task.progress_percent
        if "大纲" in message or "outline" in message.lower() or "分析" in message:
            stage, percent = "analyzing", max(percent, 15)
        if "分镜" in message or "storyboard" in message.lower():
            stage, percent = "storyboard", max(percent, 30)
        segment = re.search(r"片段\s*(\d+)\s*/\s*(\d+)", message)
        if segment:
            current, total = int(segment.group(1)), max(1, int(segment.group(2)))
            stage, percent = "segments", max(percent, 35 + round(45 * (current - 1) / total))
        if "渲染" in message:
            stage, percent = "rendering", max(percent, 70)
        if any(word in message for word in ["配音", "音频", "字幕"]):
            stage, percent = "audio", max(percent, 88)
        if "修复" in message or "重试" in message:
            stage = "retrying"
        task.current_stage = stage
        task.current_step = step
        task.progress_percent = min(99, percent) if task.state not in TERMINAL_STATES else percent
        stage_labels = ["准备素材", "分析提示词", "生成分镜", "生成片段", "渲染视频", "生成音频", "完成"]
        thresholds = [5, 15, 30, 35, 70, 88, 100]
        task.completed_steps = [label for label, threshold in zip(stage_labels, thresholds) if task.progress_percent >= threshold]
        task.remaining_steps = [label for label, threshold in zip(stage_labels, thresholds) if task.progress_percent < threshold]

    def _persist(self, task: TaskRecord) -> None:
        if not task.project_dir:
            return
        path = Path(task.project_dir) / "task_status.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(task), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _load_interrupted_tasks(self) -> None:
        if not self.projects_root.exists():
            return
        for path in self.projects_root.glob("*/task_status.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                task = TaskRecord(**payload)
            except (OSError, ValueError, TypeError):
                continue
            if task.state in {"queued", "running", "paused"}:
                task.state = "interrupted"
                task.error = "后台服务曾重启，原任务已中断，请重新提交。"
                task.current_stage = "interrupted"
                task.current_step = "后台任务已中断"
                task.finished_at = datetime.now().isoformat(timespec="seconds")
                self._persist(task)
            self._tasks[task.task_id] = task
