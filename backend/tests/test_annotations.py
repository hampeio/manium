import json
from pathlib import Path

import pytest

from backend.services.annotation_service import AnnotationService


def test_annotation_crud_persists_structured_json(tmp_path: Path):
    service = AnnotationService()
    created = service.create(
        tmp_path,
        {
            "type": "brush",
            "segment_id": "segment_02",
            "time_start": 3.25,
            "time_end": 3.25,
            "frame_index": 98,
            "shape_data": {"target_kind": "video", "shapes": [{"kind": "freehand", "points": []}]},
            "text_note": "圈出这里的遮挡",
        },
    )

    assert created["id"].startswith("ann_")
    assert created["created_at"] == created["updated_at"]
    assert service.load(tmp_path)[0]["text_note"] == "圈出这里的遮挡"

    updated = service.update(tmp_path, created["id"], {"text_note": "改为高亮这里"})
    assert updated is not None
    assert updated["text_note"] == "改为高亮这里"
    assert updated["created_at"] == created["created_at"]

    payload = json.loads((tmp_path / "annotations.json").read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["annotations"][0]["frame_index"] == 98

    assert service.delete(tmp_path, created["id"])
    assert service.load(tmp_path) == []


def test_annotation_rejects_unknown_type(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported annotation type"):
        AnnotationService().create(tmp_path, {"type": "ellipse"})
