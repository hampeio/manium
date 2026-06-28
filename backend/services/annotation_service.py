import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ANNOTATION_TYPES = {"segment", "brush", "rectangle"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnnotationService:
    """Persists structured review annotations inside a generated project."""

    filename = "annotations.json"

    def load(self, project_dir: Path) -> list[dict[str, object]]:
        path = self._project_path(project_dir) / self.filename
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        annotations = payload.get("annotations", []) if isinstance(payload, dict) else []
        return annotations if isinstance(annotations, list) else []

    def create(self, project_dir: Path, data: dict[str, object]) -> dict[str, object]:
        annotations = self.load(project_dir)
        annotation = self._normalize(data)
        now = _now_iso()
        annotation["id"] = str(data.get("id") or f"ann_{uuid4().hex}")
        annotation["created_at"] = now
        annotation["updated_at"] = now
        annotations.append(annotation)
        self._write(project_dir, annotations)
        return deepcopy(annotation)

    def update(self, project_dir: Path, annotation_id: str, data: dict[str, object]) -> dict[str, object] | None:
        annotations = self.load(project_dir)
        for index, current in enumerate(annotations):
            if str(current.get("id")) != annotation_id:
                continue
            merged = {**current, **data, "id": annotation_id}
            annotation = self._normalize(merged)
            annotation["id"] = annotation_id
            annotation["created_at"] = current.get("created_at") or _now_iso()
            annotation["updated_at"] = _now_iso()
            annotations[index] = annotation
            self._write(project_dir, annotations)
            return deepcopy(annotation)
        return None

    def delete(self, project_dir: Path, annotation_id: str) -> bool:
        annotations = self.load(project_dir)
        remaining = [item for item in annotations if str(item.get("id")) != annotation_id]
        if len(remaining) == len(annotations):
            return False
        self._write(project_dir, remaining)
        return True

    def _write(self, project_dir: Path, annotations: list[dict[str, object]]) -> None:
        root = self._project_path(project_dir)
        path = root / self.filename
        temporary = root / f".{self.filename}.tmp"
        payload = {"version": 1, "annotations": annotations}
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _project_path(project_dir: Path) -> Path:
        root = project_dir.resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError("Project directory does not exist.")
        return root

    @staticmethod
    def _normalize(data: dict[str, object]) -> dict[str, object]:
        annotation_type = str(data.get("type") or "segment")
        if annotation_type not in ANNOTATION_TYPES:
            raise ValueError(f"Unsupported annotation type: {annotation_type}")

        def optional_float(value: object) -> float | None:
            if value in (None, ""):
                return None
            return max(0.0, float(value))

        def optional_int(value: object) -> int | None:
            if value in (None, ""):
                return None
            return max(0, int(value))

        shape_data = data.get("shape_data")
        if not isinstance(shape_data, dict):
            shape_data = {}
        time_start = optional_float(data.get("time_start"))
        time_end = optional_float(data.get("time_end"))
        if time_start is not None and time_end is not None and time_end < time_start:
            time_end = time_start
        return {
            "type": annotation_type,
            "segment_id": str(data.get("segment_id") or ""),
            "time_start": time_start,
            "time_end": time_end,
            "frame_index": optional_int(data.get("frame_index")),
            "shape_data": deepcopy(shape_data),
            "text_note": str(data.get("text_note") or "").strip(),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
