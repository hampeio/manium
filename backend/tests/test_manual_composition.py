import json
from pathlib import Path

import pytest

from backend.ai.schemas import StoryboardScene, TeachingPlan
from backend.rendering.manim_renderer import RenderResult
from backend.services.generation_service import GenerationService
from backend.services.segment_media_service import SegmentMediaService


class DisabledTTS:
    def is_configured(self) -> bool:
        return False


def test_timeline_recalculates_all_segment_ranges(tmp_path: Path):
    service = SegmentMediaService(DisabledTTS())
    segments = [
        {"id": "scene_1", "duration": 2.5, "narration_text": "第一段"},
        {"id": "scene_2", "duration": 4.0, "narration_text": "第二段"},
    ]

    service.synchronize_timeline(tmp_path, segments)

    assert segments[0]["start_time"] == 0.0
    assert segments[0]["end_time"] == 2.5
    assert segments[1]["start_time"] == 2.5
    assert segments[1]["end_time"] == 6.5
    timeline = json.loads((tmp_path / "timeline_manifest.json").read_text(encoding="utf-8"))
    assert timeline["duration"] == 6.5
    assert "00:00:02,500 --> 00:00:06,500" in (tmp_path / "subtitles.srt").read_text(encoding="utf-8")


@pytest.mark.anyio
async def test_manual_composition_updates_summary_only_when_called(tmp_path: Path):
    class FakeMedia:
        def synchronize_timeline(self, _project_dir, segments):
            return segments

        def compose_project(self, project_dir, _segments):
            final = project_dir / "outputs" / "final" / "course_final.mp4"
            audio = project_dir / "outputs" / "final" / "combined_audio.wav"
            final.parent.mkdir(parents=True)
            final.write_bytes(b"final")
            audio.write_bytes(b"audio")
            return {
                "video_path": str(final.resolve()),
                "combined_audio_path": str(audio.resolve()),
                "duration": 6.0,
                "composed_at": "now",
            }

    service = object.__new__(GenerationService)
    service.segment_media = FakeMedia()
    service._load_stage_manifest = lambda _project_dir: [{"stage": 3, "is_stitching_stage": True, "status": "awaiting_compose"}]
    segment_video = tmp_path / "one.mp4"
    segment_audio = tmp_path / "one.wav"
    segment_subtitle = tmp_path / "one.srt"
    segment_video.write_bytes(b"video")
    segment_audio.write_bytes(b"audio")
    segment_subtitle.write_text("subtitle", encoding="utf-8")
    (tmp_path / "segment_manifest.json").write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": "scene_1",
                        "video_path": str(segment_video),
                        "audio_path": str(segment_audio),
                        "subtitle_path": str(segment_subtitle),
                        "duration": 6.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "final_summary.json").write_text(
        json.dumps({"compose_status": "awaiting_user", "video_path": None}), encoding="utf-8"
    )

    result = await service.compose_project(project_dir=tmp_path)

    assert result["compose_status"] == "composed"
    assert result["video_path"].endswith("course_final.mp4")
    saved = json.loads((tmp_path / "final_summary.json").read_text(encoding="utf-8"))
    assert saved["stages"][0]["status"] == "stitched"


@pytest.mark.anyio
async def test_replace_segment_never_stitches_and_marks_final_stale(tmp_path: Path):
    scene = StoryboardScene(index=1, title="局部", narration="新版旁白", visual_plan="局部画面", estimated_seconds=5)
    plan = TeachingPlan(
        image_understanding="无图片",
        teaching_goal="局部修正",
        conflict_strategy="保持主题",
        scenes=[scene],
        code_plan="仅修改当前片段",
    )
    (tmp_path / "teaching_plan.json").write_text(json.dumps(plan.model_dump(), ensure_ascii=False), encoding="utf-8")
    old_video = tmp_path / "old.mp4"
    old_video.write_bytes(b"old")
    (tmp_path / "segment_manifest.json").write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": "scene_1",
                        "segment": 1,
                        "scene_indexes": [1],
                        "video_path": str(old_video),
                        "revision": 1,
                        "duration": 5.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "final_summary.json").write_text(
        json.dumps({"video_path": str(tmp_path / "old_final.mp4"), "compose_status": "composed"}), encoding="utf-8"
    )
    rendered = tmp_path / "replacement.mp4"
    rendered.write_bytes(b"replacement")

    class Router:
        async def generate_code_for_segment(self, *_args, **_kwargs):
            return "from manim import *\nclass GeneratedTeachingScene(Scene):\n    def construct(self):\n        self.wait(1)\n"

    class FakeMedia:
        def prepare_segment(self, **kwargs):
            assert kwargs["revision"] == 2
            return {
                "video_path": str(rendered),
                "audio_path": str(tmp_path / "scene_1.wav"),
                "subtitle_path": str(tmp_path / "scene_1.srt"),
                "preview_video_path": str(rendered),
                "duration": 6.0,
                "narration_text": "新版旁白",
                "revision": 2,
                "updated_at": "now",
            }

        def synchronize_timeline(self, _project_dir, segments):
            segments[0]["start_time"] = 0.0
            segments[0]["end_time"] = 6.0
            return segments

    service = object.__new__(GenerationService)
    service.segment_media = FakeMedia()

    async def fake_render(*_args, **_kwargs):
        return RenderResult(True, "", "", rendered, [])

    async def forbidden_stitch(*_args, **_kwargs):
        raise AssertionError("segment replacement must not stitch")

    service._render_with_repairs = fake_render
    service._stitch_segment_videos = forbidden_stitch

    result = await service.replace_segment(
        project_dir=tmp_path,
        segment_id="scene_1",
        edit_prompt="只修改局部",
        model_router=Router(),
        quality="low",
    )

    assert result["video_path"] is None
    assert result["compose_status"] == "stale"
    summary = json.loads((tmp_path / "final_summary.json").read_text(encoding="utf-8"))
    assert summary["previous_final_video_path"].endswith("old_final.mp4")
    assert summary["video_path"] is None
    manifest = json.loads((tmp_path / "segment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["segments"][0]["revision"] == 2
    assert manifest["segments"][0]["audio_path"].endswith("scene_1.wav")
