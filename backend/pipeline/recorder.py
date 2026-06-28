import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


class PipelineRecorder:
    """Writes append-only pipeline events and a compact stage manifest."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.events_path = project_dir / "pipeline_events.jsonl"
        self.manifest_path = project_dir / "pipeline_manifest.json"
        self._stage_starts: dict[str, float] = {}
        self._manifest: dict[str, Any] = {
            "version": 1,
            "project_dir": str(project_dir.resolve()),
            "started_at": self._now(),
            "completed_at": None,
            "stages": [],
        }
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._write_manifest()

    @property
    def artifact_paths(self) -> dict[str, str]:
        return {
            "pipeline_manifest_path": str(self.manifest_path.resolve()),
            "pipeline_events_path": str(self.events_path.resolve()),
        }

    def record_problem_frame(
        self,
        *,
        user_prompt: str,
        has_image: bool,
        priority_rule: str,
        target_duration_seconds: int,
        quality: str,
        compact_timing: bool,
    ) -> dict[str, Any]:
        frame = {
            "mode": "direct_workflow",
            "user_prompt_preview": user_prompt[:300],
            "has_image": has_image,
            "priority_rule": priority_rule,
            "target_duration_seconds": target_duration_seconds,
            "quality": quality,
            "compact_timing": compact_timing,
            "goal": "根据当前提示词和可选图片生成 Manim 教学动画。",
        }
        self._write_json(self.project_dir / "problem_frame.json", frame)
        self.record_event("problem_frame", "info", "问题定义已记录。", frame)
        return frame

    def start_stage(self, stage: str, message: str, details: dict[str, Any] | None = None) -> None:
        self._stage_starts[stage] = perf_counter()
        self._manifest["stages"].append(
            {
                "stage": stage,
                "status": "running",
                "started_at": self._now(),
                "completed_at": None,
                "duration_seconds": None,
                "message": message,
                "details": details or {},
            }
        )
        self._write_manifest()
        self.record_event(stage, "info", message, details)

    def complete_stage(self, stage: str, message: str, details: dict[str, Any] | None = None) -> None:
        self._finish_stage(stage, "completed", message, details)

    def fail_stage(self, stage: str, message: str, details: dict[str, Any] | None = None) -> None:
        self._finish_stage(stage, "failed", message, details)

    def record_event(self, stage: str, level: str, message: str, details: dict[str, Any] | None = None) -> None:
        event = {
            "timestamp": self._now(),
            "stage": stage,
            "level": level,
            "message": message,
            "details": self._jsonable(details or {}),
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def finish(self, status: str = "completed") -> None:
        self._manifest["completed_at"] = self._now()
        self._manifest["status"] = status
        self._write_manifest()
        status_text = {"completed": "已完成", "failed": "失败", "stopped": "已停止"}.get(status, status)
        self.record_event("pipeline", "info", f"生成管线{status_text}。")

    def _finish_stage(self, stage: str, status: str, message: str, details: dict[str, Any] | None) -> None:
        duration = None
        if stage in self._stage_starts:
            duration = round(perf_counter() - self._stage_starts.pop(stage), 3)
        for item in reversed(self._manifest["stages"]):
            if item["stage"] == stage and item["status"] == "running":
                item["status"] = status
                item["completed_at"] = self._now()
                item["duration_seconds"] = duration
                item["message"] = message
                item["details"] = details or item.get("details") or {}
                break
        self._write_manifest()
        level = "error" if status == "failed" else "info"
        payload = dict(details or {})
        if duration is not None:
            payload["duration_seconds"] = duration
        self.record_event(stage, level, message, payload)

    def _write_manifest(self) -> None:
        self._write_json(self.manifest_path, self._manifest)

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._jsonable(data), ensure_ascii=False, indent=2), encoding="utf-8")

    def _jsonable(self, data: Any) -> Any:
        if isinstance(data, Path):
            return str(data.resolve())
        if isinstance(data, dict):
            return {str(key): self._jsonable(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._jsonable(value) for value in data]
        if isinstance(data, tuple):
            return [self._jsonable(value) for value in data]
        return data

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
