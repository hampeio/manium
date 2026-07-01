import json
from pathlib import Path

import pytest

from backend.core.config import Settings
from backend.services.generation_service import GenerationService
from backend.services.project_manager import ProjectManager
from backend.services.segment_media_service import SegmentMediaService


class FakeTTS:
    def is_configured(self):
        return False


def make_generation_service(tmp_path: Path) -> GenerationService:
    manager = ProjectManager(tmp_path)
    return GenerationService(Settings(default_provider="mock"), manager)


def test_segment_code_info_is_bound_to_selected_segment(tmp_path, monkeypatch):
    service = make_generation_service(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    code_one = project / "one.py"
    code_two = project / "two.py"
    code_one.write_text("from manim import *\nclass GeneratedTeachingScene(Scene):\n    pass\n", encoding="utf-8")
    code_two.write_text("# segment two\n", encoding="utf-8")
    video = project / "one.mp4"
    audio = project / "one.wav"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")
    (project / "segment_manifest.json").write_text(
        json.dumps(
            {
                "segments": [
                    {"id": "scene_1", "title": "第一段", "code_path": str(code_one), "video_path": str(video), "audio_path": str(audio)},
                    {"id": "scene_2", "title": "第二段", "code_path": str(code_two)},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(service.segment_media, "probe_duration", lambda path: 8.0 if path.suffix == ".mp4" else 10.0)

    info = service.get_segment_code_info(project_dir=project, segment_id="scene_1")

    assert info["segment_id"] == "scene_1"
    assert "GeneratedTeachingScene" in info["code"]
    assert info["video_duration"] == 8.0
    assert info["audio_duration"] == 10.0
    assert info["needs_audio_stretch"]


def test_auto_audio_policy_extends_video_and_preserves_existing_audio(tmp_path, monkeypatch):
    media = SegmentMediaService(FakeTTS())
    project = tmp_path / "project"
    rendered = tmp_path / "rendered.mp4"
    existing_audio = tmp_path / "existing.wav"
    rendered.write_bytes(b"video")
    existing_audio.write_bytes(b"audio")
    durations = {str(rendered): 6.0, str(existing_audio): 9.0}

    def probe(path):
        if str(path) in durations:
            return durations[str(path)]
        if path.parent.name == "segments" and path.suffix == ".mp4":
            return 6.0
        return 9.0 if path.suffix in {".wav", ".mp4"} else 0.0

    def extend(path, extension):
        durations[str(path)] = durations.get(str(path), 6.0) + extension

    def normalize(_source, output, duration):
        output.write_bytes(b"audio")
        durations[str(output)] = duration

    monkeypatch.setattr(media, "probe_duration", probe)
    monkeypatch.setattr(media, "_extend_video", extend)
    monkeypatch.setattr(media, "_normalize_audio", normalize)
    monkeypatch.setattr(media, "_mux_preview", lambda _v, _a, output, _d: output.write_bytes(b"preview"))

    assets = media.prepare_segment(
        project_dir=project,
        segment_id="scene_1",
        rendered_video=rendered,
        narration_text="不变的旁白",
        revision=2,
        previous={"audio_path": str(existing_audio), "narration_text": "不变的旁白"},
        timing_policy="auto_audio",
    )

    assert assets["duration"] == 9.0
    assert assets["manim_video_duration"] == 6.0
    assert assets["audio_duration"] == 9.0
    assert assets["timing_adjustment"] == "video_extended_to_audio"
    assert assets["duration_aligned"]


@pytest.mark.anyio
async def test_manual_segment_code_requires_generated_scene(tmp_path):
    service = make_generation_service(tmp_path)

    with pytest.raises(ValueError, match="GeneratedTeachingScene"):
        await service.render_segment_code(
            project_dir=tmp_path,
            segment_id="scene_1",
            manim_code="print('wrong segment')",
            quality="low",
        )
