import asyncio
import json
import shutil
import traceback
from collections.abc import Callable
from pathlib import Path

from backend.ai.model_router import ModelRouter
from backend.ai.schemas import GeneratedAnimation, GenerationStrategy, StoryboardScene, TeachingPlan
from backend.core.config import Settings
from backend.image_nodes.validation import transcode_or_compress_placeholder, validate_image
from backend.pipeline.recorder import PipelineRecorder
from backend.rendering.code_sanitizer import sanitize_manim_code
from backend.rendering.manim_renderer import ManimRenderer, RenderResult
from backend.rendering.static_checker import run_static_check
from backend.rendering.visual_guard import run_segment_diversity_check, run_visual_consistency_check
from backend.services.project_manager import ProjectManager
from backend.services.segment_media_service import SegmentMediaService
from backend.services.subtitle_service import build_subtitles
from backend.services.tts_service import TTSService


ProgressCallback = Callable[[str], None]
PauseChecker = Callable[[], bool]
PartialCallback = Callable[[dict[str, object]], None]


class GenerationService:
    """Coordinates project creation, AI planning, Manim rendering, and repair."""

    def __init__(self, settings: Settings, project_manager: ProjectManager):
        self.settings = settings
        self.project_manager = project_manager
        self.renderer = ManimRenderer(settings.manim_command)
        self.tts_service = TTSService(settings)
        self.segment_media = SegmentMediaService(self.tts_service)

    async def run(
        self,
        *,
        project_dir: Path,
        user_prompt: str,
        uploaded_image: Path | None,
        model_router: ModelRouter,
        quality: str,
        project_manager: ProjectManager | None = None,
        progress: ProgressCallback | None = None,
        pause_checker: PauseChecker | None = None,
        partial_update: PartialCallback | None = None,
        total_duration_seconds: int = 300,
        compact_timing: bool = False,
        preferred_scene_count: int = 0,
    ) -> dict[str, object]:
        writer = project_manager or self.project_manager
        emit = progress or (lambda _message: None)
        total_duration_seconds = self._clamp_total_duration(total_duration_seconds)
        recorder = PipelineRecorder(project_dir)
        try:
            emit("第一阶段（共三阶段）：正在准备大纲、输入内容和教学意图。")
            recorder.start_stage("prepare", "Preparing inputs and project frame.")
            image_context = await self._prepare_image(project_dir, uploaded_image, writer)
            await self._pause_if_requested(pause_checker, emit)
            priority_rule = self._priority_rule(user_prompt, uploaded_image)
            writer.write_text(project_dir, "inputs/user_prompt.txt", user_prompt or "")
            recorder.record_problem_frame(
                user_prompt=user_prompt or "",
                has_image=uploaded_image is not None,
                priority_rule=priority_rule,
                target_duration_seconds=total_duration_seconds,
                quality=quality,
                compact_timing=compact_timing,
            )
            recorder.complete_stage("prepare", "Inputs prepared.", {"has_image": uploaded_image is not None})

            emit(f"目标总时长：{total_duration_seconds} 秒。")
            emit("第一阶段（共三阶段）：正在调用模型生成大纲、时长规划和调用次数。")
            recorder.start_stage("outline", "Calling model for outline and generation strategy.")
            strategy = await model_router.plan_generation_strategy(
                user_prompt,
                uploaded_image,
                image_context,
                priority_rule,
                total_duration_seconds,
            )
            strategy = self._normalize_strategy(strategy, total_duration_seconds, preferred_scene_count)
            writer.write_json(project_dir, "generation_strategy.json", strategy.model_dump())
            emit(f"大纲已完成。计划调用模型 {strategy.ai_call_count} 次，分镜批次 {len(strategy.batches)} 个。")
            recorder.complete_stage(
                "outline",
                "Generation strategy ready.",
                {"ai_call_count": strategy.ai_call_count, "batch_count": len(strategy.batches)},
            )
            await self._pause_if_requested(pause_checker, emit)

            emit("第二阶段（共三阶段）：正在根据大纲生成细化分镜。")
            recorder.start_stage("storyboard", "Generating storyboard batches.")
            scenes: list[StoryboardScene] = []
            for batch in strategy.batches:
                emit(f"分镜批次 {batch.batch_index}/{len(strategy.batches)}：{batch.title}")
                recorder.record_event(
                    "storyboard",
                    "info",
                    "Calling model for storyboard batch.",
                    {"batch_index": batch.batch_index, "title": batch.title, "scene_count": batch.scene_count},
                )
                result = await model_router.generate_storyboard_batch(
                    strategy,
                    batch,
                    len(scenes) + 1,
                    [scene.title for scene in scenes],
                )
                scenes.extend(result.scenes)
                writer.write_json(project_dir, f"storyboard_batches/batch_{batch.batch_index}.json", result.model_dump())
                await self._pause_if_requested(pause_checker, emit)

            plan = TeachingPlan(
                image_understanding=strategy.image_understanding,
                teaching_goal=strategy.teaching_goal,
                conflict_strategy=strategy.conflict_strategy,
                scenes=self._renumber_and_scale_scenes(scenes, total_duration_seconds),
                code_plan=strategy.code_plan,
            )
            if compact_timing:
                emit("已启用紧凑节奏：正在减少分镜之间的空白等待。")
                plan.code_plan = (
                    f"{plan.code_plan}\n"
                    "COMPACT_TIMING: compact timing mode; avoid long blank waits; keep each wait near 2-4 seconds."
                )
            emit(f"分镜已完成：共 {len(plan.scenes)} 个细化片段。")
            recorder.complete_stage("storyboard", "Storyboard ready.", {"scene_count": len(plan.scenes)})

            visual_design = self._build_visual_design_guidance(plan)
            writer.write_text(project_dir, "visual_design.md", visual_design)
            plan.code_plan = (
                f"{plan.code_plan}\n\n"
                "VISUAL_DESIGN_SOURCE_OF_TRUTH:\n"
                f"{visual_design}"
            )
            recorder.record_event("visual_design", "info", "Executable visual design guidance written.", {"path": str((project_dir / "visual_design.md").resolve())})

            generated = GeneratedAnimation(plan=plan, manim_code="")
            self._write_plan_artifacts(project_dir, generated, writer)
            provisional_stages = self._build_stage_data(plan.scenes, total_duration_seconds, False)
            provisional_segments = self._build_scene_segment_data(plan.scenes, provisional_stages, [], None)
            writer.write_json(project_dir, "stage_manifest.json", {"mode": "three_stage_quick_generation", "stages": provisional_stages})
            writer.write_json(project_dir, "segment_manifest.json", {"mode": "planned_segment_manifest", "segments": provisional_segments})
            if partial_update:
                partial_update(
                    {
                        "project_dir": str(project_dir.resolve()),
                        "storyboard": [scene.model_dump() for scene in plan.scenes],
                        "stages": provisional_stages,
                        "segments": provisional_segments,
                        "video_path": None,
                    }
                )

            emit("第二阶段（共三阶段）：正在生成并渲染分段 Manim 课程。")
            recorder.start_stage("render_course", "Generating Manim code and rendering course.")
            generated, final_result, segment_outputs = await self._render_segmented_or_single(
                project_dir=project_dir,
                plan=plan,
                strategy=strategy,
                model_router=model_router,
                quality=quality,
                writer=writer,
                emit=emit,
                total_duration_seconds=total_duration_seconds,
                recorder=recorder,
                partial_update=partial_update,
            )
            if final_result.success:
                segment_outputs = await self._prepare_segment_assets(project_dir, plan, segment_outputs, emit)
            if final_result.success:
                recorder.complete_stage("render_course", "Course render completed.", {"segments": len(segment_outputs)})
            else:
                recorder.fail_stage("render_course", "Course render failed.", {"segments": len(segment_outputs)})
            emit("模型输入与输出记录已保存。")
            await self._pause_if_requested(pause_checker, emit)

            emit("第三阶段（共三阶段）：正在拼接、导出最终视频并写入结果摘要。")
            recorder.start_stage("export", "Writing summary and optional narration.")
            await self._pause_if_requested(pause_checker, emit)
            summary = self._build_summary(project_dir, generated, final_result, writer)
            summary["segment_render_outputs"] = segment_outputs
            summary["tts_enabled"] = self.tts_service.is_configured()
            summary["tts_status"] = "segment_assets_ready" if final_result.success else "segment_assets_incomplete"
            summary["audio_path"] = None
            summary["compose_status"] = "awaiting_user"
            summary["segments_ready"] = bool(segment_outputs) and all(
                item.get("status") in {"rendered", "replaced"} for item in segment_outputs
            )
            stages = self._write_stage_manifest(project_dir, generated, summary, writer, total_duration_seconds)
            self._write_segment_manifest(project_dir, generated, summary, writer, stages, segment_outputs)
            summary["total_duration_seconds"] = total_duration_seconds
            summary["stage_manifest_path"] = str((project_dir / "stage_manifest.json").resolve())
            summary["segment_manifest_path"] = str((project_dir / "segment_manifest.json").resolve())
            summary["stages"] = self._load_stage_manifest(project_dir)
            summary["segments"] = self._load_segment_manifest(project_dir)
            summary.update(recorder.artifact_paths)
            writer.write_json(project_dir, "final_summary.json", summary)
            recorder.complete_stage("export", "Project summary written.", {"success": final_result.success})
            recorder.finish("completed" if final_result.success else "failed")
            return summary
        except Exception as exc:
            error = "".join(traceback.format_exception(exc))
            writer.write_text(project_dir, "logs/backend_error.log", error)
            recorder.record_event("pipeline", "error", str(exc), {"traceback_path": str((project_dir / "logs" / "backend_error.log").resolve())})
            recorder.finish("failed")
            raise

    async def replace_segment(
        self,
        *,
        project_dir: Path,
        segment_id: str,
        edit_prompt: str,
        model_router: ModelRouter,
        quality: str,
        progress: ProgressCallback | None = None,
        partial_update: PartialCallback | None = None,
    ) -> dict[str, object]:
        """Regenerate only one segment; never compose the overall video here."""

        emit = progress or (lambda _message: None)
        writer = ProjectManager(project_dir)
        plan_path = project_dir / "teaching_plan.json"
        manifest_path = project_dir / "segment_manifest.json"
        if not plan_path.exists() or not manifest_path.exists():
            raise FileNotFoundError("Project teaching plan or segment manifest is missing.")

        plan_data = json.loads(plan_path.read_text(encoding="utf-8", errors="replace"))
        plan = TeachingPlan.model_validate(plan_data)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
        segments = manifest.get("segments", [])
        target = next((segment for segment in segments if str(segment.get("id")) == segment_id), None)
        if not target:
            raise ValueError(f"Segment not found: {segment_id}")

        scene_indexes = [int(value) for value in target.get("scene_indexes", [])] or [int(str(segment_id).split("_")[-1])]
        scenes = [scene for scene in plan.scenes if scene.index in scene_indexes]
        if not scenes:
            raise ValueError("选中的片段没有匹配到分镜。")

        revision = int(target.get("revision") or 1) + 1
        segment_dir = project_dir / "segments" / f"replacement_{revision:03d}_{segment_id}"
        for folder in ["logs", "repairs", "outputs"]:
            (segment_dir / folder).mkdir(parents=True, exist_ok=True)

        segment_plan = TeachingPlan(
            image_understanding=plan.image_understanding,
            teaching_goal=plan.teaching_goal,
            conflict_strategy=plan.conflict_strategy,
            scenes=scenes,
            code_plan=(
                f"{plan.code_plan}\n\n"
                "SEGMENT_REPLACEMENT_REQUEST:\n"
                f"{edit_prompt.strip() or 'Regenerate only this segment while preserving the teaching goal.'}"
            ),
        )
        segment_duration = max(1, round(sum(scene.estimated_seconds for scene in scenes)))
        emit(f"正在修改 {segment_id}：生成新版 Manim 代码。")
        code = await model_router.generate_code_for_segment(
            segment_plan,
            segment_index=int(target.get("segment") or scene_indexes[0]),
            segment_count=max(1, len(segments)),
            segment_duration_seconds=segment_duration,
        )
        code = sanitize_manim_code(code)
        scene_file = writer.write_text(segment_dir, "scene.py", code)
        writer.write_text(segment_dir, "original_manim_code.py", code)
        emit(f"正在修改 {segment_id}：渲染新版片段。")
        result = await self._render_with_repairs(
            segment_dir,
            scene_file,
            code,
            GeneratedAnimation(plan=segment_plan, manim_code=code),
            model_router,
            quality,
            writer,
            emit,
            None,
        )
        if not result.success or not result.video_path:
            raise RuntimeError(result.stderr or result.stdout or "片段替换渲染失败。")

        if not target.get("original_video_path") and target.get("video_path"):
            target["original_video_path"] = target["video_path"]
            target["original_preview_path"] = target.get("preview_video_path") or target["video_path"]
        if not target.get("audio_source_path"):
            legacy_audio = project_dir / "audio" / f"scene_{scene_indexes[0]:02d}.mp3"
            if legacy_audio.exists():
                target["audio_source_path"] = str(legacy_audio.resolve())
        narration = "\n".join(scene.narration for scene in scenes if scene.narration).strip()
        assets = await asyncio.to_thread(
            self.segment_media.prepare_segment,
            project_dir=project_dir,
            segment_id=segment_id,
            rendered_video=result.video_path,
            narration_text=narration,
            revision=revision,
            previous=target,
        )
        target.update(assets)
        target.update(
            {
                "segment_id": segment_id,
                "status": "replaced",
                "project_dir": str(segment_dir.resolve()),
                "code_path": str(scene_file.resolve()),
                "estimated_seconds": assets["duration"],
            }
        )
        self.segment_media.synchronize_timeline(project_dir, segments)
        total_duration = int(round(sum(float(item.get("duration") or 0) for item in segments))) or 300
        stages = self._build_stage_data(plan.scenes, total_duration, True)
        writer.write_json(project_dir, "stage_manifest.json", {"mode": "awaiting_manual_composition", "stages": stages})
        writer.write_json(project_dir, "segment_manifest.json", {"mode": "replacement_segment_manifest", "segments": segments})

        summary_path = project_dir / "final_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8", errors="replace")) if summary_path.exists() else {}
        if summary.get("video_path"):
            summary["previous_final_video_path"] = summary["video_path"]
        summary.update(
            {
                "video_path": None,
                "output_video_path": None,
                "compose_status": "stale",
                "final_video_stale": True,
                "segments": segments,
                "stages": stages,
                "manim_code": code,
                "last_replaced_segment": segment_id,
            }
        )
        writer.write_json(project_dir, "final_summary.json", summary)
        partial = {
            "project_dir": str(project_dir.resolve()),
            "segments": segments,
            "stages": stages,
            "video_path": None,
            "segment_preview_path": target.get("preview_video_path") or target.get("video_path"),
            "compose_status": "stale",
        }
        if partial_update:
            partial_update(partial)
        return partial | {"success": True, "storyboard": [scene.model_dump() for scene in plan.scenes]}

    async def compose_project(
        self,
        *,
        project_dir: Path,
        progress: ProgressCallback | None = None,
    ) -> dict[str, object]:
        """Compose all latest segment revisions only after an explicit user action."""

        emit = progress or (lambda _message: None)
        manifest_path = project_dir / "segment_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("The project does not contain a segment manifest.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
        segments = manifest.get("segments", [])
        if not segments:
            raise ValueError("The timeline has no segments to compose.")
        segments = await self._ensure_manifest_assets(project_dir, segments, emit)
        self.segment_media.synchronize_timeline(project_dir, segments)
        emit("Checking video, audio, subtitle, and duration consistency for every segment.")
        composition = await asyncio.to_thread(self.segment_media.compose_project, project_dir, segments)
        emit("Latest segment revisions have been composed into the overall video.")
        writer = ProjectManager(project_dir)
        writer.write_json(project_dir, "segment_manifest.json", {"mode": "composed_segment_manifest", "segments": segments})
        summary_path = project_dir / "final_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8", errors="replace")) if summary_path.exists() else {}
        summary.update(composition)
        summary.update(
            {
                "success": True,
                "project_dir": str(project_dir.resolve()),
                "output_video_path": composition["video_path"],
                "audio_path": composition["combined_audio_path"],
                "compose_status": "composed",
                "final_video_stale": False,
                "segments": segments,
            }
        )
        stages = self._load_stage_manifest(project_dir)
        for stage in stages:
            if stage.get("is_stitching_stage"):
                stage["status"] = "stitched"
                stage["video_path"] = composition["video_path"]
        writer.write_json(project_dir, "stage_manifest.json", {"mode": "manual_composition", "stages": stages})
        summary["stages"] = stages
        writer.write_json(project_dir, "final_summary.json", summary)
        return summary

    async def _prepare_segment_assets(
        self,
        project_dir: Path,
        plan: TeachingPlan,
        outputs: list[dict[str, object]],
        emit: ProgressCallback,
    ) -> list[dict[str, object]]:
        scenes_by_index = {scene.index: scene for scene in plan.scenes}
        for output in outputs:
            if not output.get("success") or not output.get("video_path"):
                continue
            scene_indexes = [int(value) for value in output.get("scene_indexes", [])]
            if not scene_indexes:
                continue
            segment_id = f"scene_{scene_indexes[0]}"
            selected_scenes = [scenes_by_index[index] for index in scene_indexes if index in scenes_by_index]
            narration = "\n".join(scene.narration for scene in selected_scenes if scene.narration).strip()
            emit(f"Synchronizing video, audio, and subtitles for {segment_id}.")
            assets = await asyncio.to_thread(
                self.segment_media.prepare_segment,
                project_dir=project_dir,
                segment_id=segment_id,
                rendered_video=Path(str(output["video_path"])),
                narration_text=narration,
                revision=1,
                previous=None,
            )
            output.update(assets)
            output["id"] = segment_id
            output["segment_id"] = segment_id
            output["title"] = selected_scenes[0].title if selected_scenes else output.get("title")
            output["status"] = "rendered"
            output["estimated_seconds"] = assets["duration"]
        self.segment_media.synchronize_timeline(project_dir, outputs)
        return outputs

    async def _ensure_manifest_assets(
        self,
        project_dir: Path,
        segments: list[dict[str, object]],
        emit: ProgressCallback,
    ) -> list[dict[str, object]]:
        """Upgrade legacy manifests to independent per-segment assets before manual composition."""

        for index, segment in enumerate(segments, start=1):
            required = [segment.get("video_path"), segment.get("audio_path"), segment.get("subtitle_path")]
            if all(value and Path(str(value)).exists() for value in required):
                continue
            source_video = Path(str(segment.get("video_path") or ""))
            if not source_video.exists():
                raise FileNotFoundError(f"Missing video for segment {segment.get('id') or index}.")
            segment_id = str(segment.get("id") or f"scene_{index}")
            narration = str(segment.get("narration_text") or segment.get("narration") or "")
            legacy_audio = project_dir / "audio" / f"scene_{index:02d}.mp3"
            previous = dict(segment)
            previous.setdefault("original_video_path", str(source_video.resolve()))
            previous.setdefault("original_preview_path", segment.get("preview_video_path") or str(source_video.resolve()))
            if legacy_audio.exists():
                previous["audio_source_path"] = str(legacy_audio.resolve())
                previous["narration_text"] = narration
            revision = max(1, int(segment.get("revision") or 1))
            emit(f"Preparing independent media assets for legacy segment {segment_id}.")
            assets = await asyncio.to_thread(
                self.segment_media.prepare_segment,
                project_dir=project_dir,
                segment_id=segment_id,
                rendered_video=source_video,
                narration_text=narration,
                revision=revision,
                previous=previous,
            )
            segment.update(assets)
            segment["id"] = segment_id
            segment["segment_id"] = segment_id
            segment["status"] = segment.get("status") or "rendered"
        return segments

    async def _pause_if_requested(self, pause_checker: PauseChecker | None, emit: ProgressCallback) -> None:
        if not pause_checker:
            return
        if pause_checker():
            emit("任务已暂停，正在等待继续。")
        while pause_checker():
            await asyncio.sleep(0.5)

    async def _prepare_image(self, project_dir: Path, uploaded_image: Path | None, writer: ProjectManager) -> str:
        if not uploaded_image:
            return "No image uploaded. The animation will be generated from the user prompt."
        metadata = validate_image(uploaded_image)
        transcode_or_compress_placeholder(uploaded_image)
        context = (
            "Image saved and format check passed: "
            f"format={metadata['format']}, width={metadata['width']}, height={metadata['height']}. "
            "Advanced OCR/detection nodes are reserved for a later version."
        )
        writer.write_json(project_dir, "image_understanding.json", {"status": "placeholder", "context": context, "metadata": metadata})
        return context

    def _priority_rule(self, user_prompt: str, uploaded_image: Path | None) -> str:
        if user_prompt and uploaded_image:
            return "Prompt and image are both provided. The prompt has priority; the image is used as content evidence and visual reference."
        if uploaded_image:
            return "Only image is provided. The image content is interpreted first."
        return "Only prompt is provided. The animation is generated from the prompt."

    def _clamp_total_duration(self, value: int) -> int:
        try:
            duration = int(value)
        except (TypeError, ValueError):
            duration = 300
        return max(300, min(duration, 1800))

    def _normalize_scene_durations(self, generated: GeneratedAnimation, total_duration_seconds: int) -> None:
        """Scales storyboard timings so subtitles and stage previews match the requested duration."""

        generated.plan.scenes = self._renumber_and_scale_scenes(generated.plan.scenes, total_duration_seconds)

    def _renumber_and_scale_scenes(self, scenes: list[StoryboardScene], total_duration_seconds: int) -> list[StoryboardScene]:
        """Renumbers scenes and scales storyboard timings without changing their content."""

        if not scenes:
            return []
        base = total_duration_seconds // len(scenes)
        remainder = total_duration_seconds - base * len(scenes)
        for index, scene in enumerate(scenes):
            scene.index = index + 1
            scene.estimated_seconds = float(base + (1 if index < remainder else 0))
        return scenes

    def _normalize_strategy(self, strategy: GenerationStrategy, total_duration_seconds: int, preferred_scene_count: int = 0) -> GenerationStrategy:
        """Keeps the first outline call authoritative while enforcing local safety bounds."""

        strategy.target_duration_seconds = total_duration_seconds
        if not strategy.batches:
            return strategy
        if preferred_scene_count > 0:
            target_scenes = max(6, min(60, int(preferred_scene_count)))
            batch_count = max(1, min(len(strategy.batches), target_scenes // 2))
            strategy.batches = strategy.batches[:batch_count]
            base_scene_count = target_scenes // batch_count
            scene_remainder = target_scenes - base_scene_count * batch_count
            for index, batch in enumerate(strategy.batches):
                batch.scene_count = base_scene_count + (1 if index < scene_remainder else 0)
        total_scenes = sum(batch.scene_count for batch in strategy.batches)
        strategy.estimated_scene_count = total_scenes
        # One outline call has already happened; then each batch creates
        # storyboard scenes, and each final storyboard scene gets its own
        # Manim code/render pass so previews and replacement are precise.
        strategy.ai_call_count = 1 + len(strategy.batches) + total_scenes
        base = total_duration_seconds // len(strategy.batches)
        remainder = total_duration_seconds - base * len(strategy.batches)
        for index, batch in enumerate(strategy.batches):
            batch.batch_index = index + 1
            batch.duration_seconds = base + (1 if index < remainder else 0)
        return strategy

    def _write_plan_artifacts(self, project_dir: Path, generated: GeneratedAnimation, writer: ProjectManager) -> None:
        plan = generated.plan.model_dump()
        srt, timeline = build_subtitles(generated.plan.scenes)
        writer.write_json(project_dir, "teaching_plan.json", plan)
        writer.write_text(project_dir, "image_understanding.txt", generated.plan.image_understanding)
        writer.write_text(project_dir, "teaching_goal.txt", generated.plan.teaching_goal)
        writer.write_text(project_dir, "code_plan.txt", generated.plan.code_plan)
        writer.write_json(project_dir, "storyboard.json", [scene.model_dump() for scene in generated.plan.scenes])
        writer.write_text(project_dir, "subtitles.srt", srt)
        writer.write_json(project_dir, "timeline_subtitles.json", timeline)
        writer.write_json(project_dir, "narration.json", [{"scene": scene.index, "text": scene.narration} for scene in generated.plan.scenes])

    def _build_visual_design_guidance(self, plan: TeachingPlan) -> str:
        """Creates a ManimCat-style executable storyboard guide without another model call."""

        lines = [
            "# Design",
            "",
            "## Goal",
            f"- 教学目标：{plan.teaching_goal}",
            "- 代码生成必须以 storyboard.visual_plan 为画面事实来源。",
            "- 不得复用旧主题素材；非数学主题不得使用坐标轴/向量投影占位图。",
            "",
            "## Layout",
            "- 稳定布局：顶部短标题；左侧主图解区域；右侧关键词/关系卡片；底部时间线或阶段进度。",
            "- 每个分镜只新增一个主要视觉动作，避免文字堆叠。",
            "",
            "## Object Rules",
            "- persistent：主题标题、主图解区域、阶段进度条。",
            "- temporary：当前分镜字幕、辅助箭头、强调圈、临时说明卡片。",
            "- exit：每个分镜结束时清理临时对象，保留主结构和进度状态。",
            "",
            "## Shot Plan",
        ]
        for scene in plan.scenes:
            lines.extend(
                [
                    f"### Shot {scene.index}: {scene.title}",
                    f"duration {round(scene.estimated_seconds)}s",
                    "layout center_focus_side_note",
                    f"focus {scene.title}",
                    f"enter {scene.visual_plan}",
                    "keep title, main_visual_area, progress_timeline",
                    "exit previous_temp_labels, previous_temp_arrows",
                    f"note narration: {scene.narration}",
                    "- start state: 保留上一分镜的主结构。",
                    "- action: 按 visual_plan 新增或变换一个可见教学对象。",
                    "- end state: 当前重点被高亮，临时文字不遮挡主图。",
                    "",
                ]
            )
        lines.extend(
            [
                "## Review",
                "- overlap check: 文字不得压住主图。",
                "- lifecycle check: 临时对象必须退出。",
                "- focus check: 每个分镜只突出一个重点。",
                "- pacing check: 不靠长等待凑时长。",
            ]
        )
        return "\n".join(lines)

    async def _render_segmented_or_single(
        self,
        *,
        project_dir: Path,
        plan: TeachingPlan,
        strategy: GenerationStrategy,
        model_router: ModelRouter,
        quality: str,
        writer: ProjectManager,
        emit: ProgressCallback,
        total_duration_seconds: int,
        recorder: PipelineRecorder | None = None,
        partial_update: PartialCallback | None = None,
    ) -> tuple[GeneratedAnimation, RenderResult, list[dict[str, object]]]:
        segments = self._build_storyboard_segments(plan, strategy)
        if len(segments) <= 1:
            return await self._render_single_course(project_dir, plan, model_router, quality, writer, emit, total_duration_seconds, recorder)

        segment_outputs: list[dict[str, object]] = []
        segment_codes: list[str] = []
        emit(f"已启用分段渲染：共 {len(segments)} 段，每个分镜单独生成视频。")
        for index, scenes in enumerate(segments, start=1):
            segment_duration = max(1, round(sum(scene.estimated_seconds for scene in scenes)))
            segment_dir = project_dir / "segments" / f"part_{index:02d}"
            for folder in ["logs", "repairs", "outputs"]:
                (segment_dir / folder).mkdir(parents=True, exist_ok=True)
            segment_plan = TeachingPlan(
                image_understanding=plan.image_understanding,
                teaching_goal=plan.teaching_goal,
                conflict_strategy=plan.conflict_strategy,
                scenes=scenes,
                code_plan=plan.code_plan,
            )
            writer.write_json(project_dir, f"segments/part_{index:02d}/storyboard.json", [scene.model_dump() for scene in scenes])
            emit(f"片段 {index}/{len(segments)}：正在为 {len(scenes)} 个分镜生成 Manim 代码。")
            if recorder:
                recorder.record_event("codegen", "info", "Generating segment Manim code.", {"segment": index, "scene_count": len(scenes)})
            code = await model_router.generate_code_for_segment(
                segment_plan,
                segment_index=index,
                segment_count=len(segments),
                segment_duration_seconds=segment_duration,
            )
            code = sanitize_manim_code(code)
            previous_codes = [item.split("\n", 1)[-1] for item in segment_codes]
            diversity_check = run_segment_diversity_check(code, previous_codes)
            writer.write_json(
                project_dir,
                f"segments/part_{index:02d}/logs/segment_diversity_initial.json",
                diversity_check.to_dict(),
            )
            if not diversity_check.success:
                emit(f"片段 {index}/{len(segments)}：检测到视觉重复，正在重写当前片段。")
                if recorder:
                    recorder.record_event(
                        "visual_guard",
                        "warning",
                        "Segment visual structure was too similar or contained placeholder content.",
                        {"segment": index, **diversity_check.to_dict()},
                    )
                writer.write_text(project_dir, f"segments/part_{index:02d}/repairs/diversity_before.py", code)
                repair = await model_router.repair_code(
                    self._repair_goal_context(segment_plan),
                    code,
                    (
                        diversity_check.error
                        + "\n只重写当前片段。严格实现当前 visual_plan，改变主要图形对象、空间布局和动画动作；"
                        "不能只改标题或标签，不能添加完成提示、占位卡片或流程自述。"
                    ),
                )
                code = sanitize_manim_code(repair.repaired_code)
                writer.write_text(project_dir, f"segments/part_{index:02d}/repairs/diversity_after.py", code)
                diversity_check = run_segment_diversity_check(code, previous_codes)
                writer.write_json(
                    project_dir,
                    f"segments/part_{index:02d}/logs/segment_diversity_after_rewrite.json",
                    diversity_check.to_dict(),
                )
                if not diversity_check.success:
                    emit(f"片段 {index}/{len(segments)}：重写后仍较为相似，将记录警告并继续渲染。")
            segment_codes.append(f"# Segment {index}\n{code}")
            scene_file = writer.write_text(project_dir, f"segments/part_{index:02d}/scene.py", code)
            writer.write_text(project_dir, f"segments/part_{index:02d}/original_manim_code.py", code)
            emit(f"片段 {index}/{len(segments)}：正在渲染。")
            result = await self._render_with_repairs(
                segment_dir,
                scene_file,
                code,
                GeneratedAnimation(plan=segment_plan, manim_code=code),
                model_router,
                quality,
                ProjectManager(segment_dir),
                emit,
                recorder,
            )
            output = {
                "segment": index,
                "id": f"part_{index:02d}",
                "title": f"片段 {index}",
                "stage": self._stage_for_segment(index, len(segments)),
                "scene_indexes": [scene.index for scene in scenes],
                "success": result.success,
                "status": "rendered" if result.success and result.video_path else "failed",
                "video_path": str(result.video_path.resolve()) if result.video_path else None,
                "project_dir": str(segment_dir.resolve()),
                "code_path": str(scene_file.resolve()),
                "estimated_seconds": segment_duration,
            }
            segment_outputs.append(output)
            if not result.success or not result.video_path:
                emit(f"片段 {index} 失败。已保留成功片段的预览，不使用整片后备视频。")
                failed = RenderResult(False, result.stdout, result.stderr or f"Segment {index} failed.", None, result.command)
                return GeneratedAnimation(plan=plan, manim_code="\n\n".join(segment_codes)), failed, segment_outputs
            self._write_live_segment_manifest(project_dir, plan, total_duration_seconds, segment_outputs, None, writer)
            if partial_update:
                partial_update(self._build_partial_result(project_dir, plan, total_duration_seconds, segment_outputs, None))

        aggregate_code = "\n\n".join(segment_codes)
        writer.write_text(project_dir, "scene.py", aggregate_code)
        writer.write_text(project_dir, "original_manim_code.py", aggregate_code)
        generated = GeneratedAnimation(plan=plan, manim_code=aggregate_code)
        if recorder:
            recorder.record_event("compose", "info", "Segments ready; waiting for explicit manual composition.", {"video_count": len(segment_outputs)})
        self._write_live_segment_manifest(project_dir, plan, total_duration_seconds, segment_outputs, None, writer)
        if partial_update:
            partial_update(self._build_partial_result(project_dir, plan, total_duration_seconds, segment_outputs, None))
        ready = RenderResult(True, "Segments rendered; final composition not requested.", "", None, [])
        return generated, ready, segment_outputs

    async def _render_single_course(
        self,
        project_dir: Path,
        plan: TeachingPlan,
        model_router: ModelRouter,
        quality: str,
        writer: ProjectManager,
        emit: ProgressCallback,
        total_duration_seconds: int,
        recorder: PipelineRecorder | None = None,
    ) -> tuple[GeneratedAnimation, RenderResult, list[dict[str, object]]]:
        emit("正在生成完整的 Manim 源文件。")
        if recorder:
            recorder.record_event("codegen", "info", "Generating single Manim source.", {"scene_count": len(plan.scenes)})
        manim_code = await model_router.generate_code_from_plan(plan, total_duration_seconds)
        generated = GeneratedAnimation(plan=plan, manim_code=sanitize_manim_code(manim_code))
        scene_file = writer.write_text(project_dir, "scene.py", generated.manim_code)
        writer.write_text(project_dir, "original_manim_code.py", generated.manim_code)
        emit("正在渲染单个 Manim 视频。")
        result = await self._render_with_repairs(
            project_dir,
            scene_file,
            generated.manim_code,
            generated,
            model_router,
            quality,
            writer,
            emit,
            recorder,
        )
        outputs = [
            {
                "segment": 1,
                "id": f"scene_{plan.scenes[0].index}" if plan.scenes else "scene_1",
                "title": plan.scenes[0].title if plan.scenes else "Segment 1",
                "scene_indexes": [scene.index for scene in plan.scenes],
                "success": result.success,
                "status": "rendered" if result.success and result.video_path else "failed",
                "video_path": str(result.video_path.resolve()) if result.video_path else None,
                "project_dir": str(project_dir.resolve()),
                "code_path": str(scene_file.resolve()),
            }
        ]
        return generated, result, outputs

    def _build_storyboard_segments(self, plan: TeachingPlan, strategy: GenerationStrategy) -> list[list[StoryboardScene]]:
        """Render every storyboard scene as an independent preview segment.

        Strategy batches are only for reducing storyboard token pressure.
        They must not decide video boundaries, otherwise several UI segment
        chips point to the same mp4 and replacement cannot target one beat.
        """

        return [[scene] for scene in plan.scenes]

    async def _stitch_segment_videos(self, project_dir: Path, videos: list[Path], emit: ProgressCallback) -> RenderResult:
        if len(videos) == 1:
            return RenderResult(True, "Single segment; stitching skipped.", "", videos[0], [])
        stitch_dir = project_dir / "stitched"
        stitch_dir.mkdir(parents=True, exist_ok=True)
        parts_dir = stitch_dir / "parts"
        if parts_dir.exists():
            shutil.rmtree(parts_dir)
        parts_dir.mkdir(parents=True, exist_ok=True)
        list_file = stitch_dir / "concat_list.txt"
        list_lines = []
        for index, video in enumerate(videos, start=1):
            part_name = f"part_{index:03d}.mp4"
            shutil.copy2(video, parts_dir / part_name)
            list_lines.append(f"file 'parts/{part_name}'")
        list_file.write_text("\n".join(list_lines), encoding="utf-8")
        output = stitch_dir / "course_final.mp4"
        command = [self._ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt", "-c", "copy", "course_final.mp4"]
        emit("正在使用 ffmpeg 拼接已渲染片段。")
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(stitch_dir.resolve()),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await process.communicate()
        except FileNotFoundError as exc:
            return RenderResult(False, "", str(exc), None, command, environment_error=True)
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        (stitch_dir / "stitch_stdout.log").write_text(stdout, encoding="utf-8")
        (stitch_dir / "stitch_stderr.log").write_text(stderr, encoding="utf-8")
        return RenderResult(process.returncode == 0 and output.exists(), stdout, stderr, output if output.exists() else None, command)

    def _ffmpeg_exe(self) -> str:
        found = shutil.which("ffmpeg")
        if found:
            return found
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            raise FileNotFoundError("找不到 ffmpeg。请安装 ffmpeg，或安装 imageio-ffmpeg。") from exc

    async def _render_checked(
        self,
        project_dir: Path,
        scene_file: Path,
        quality: str,
        writer: ProjectManager,
        attempt_label: str,
        recorder: PipelineRecorder | None,
        plan: TeachingPlan,
    ) -> RenderResult:
        check = run_static_check(scene_file)
        writer.write_json(project_dir, f"logs/static_check_{attempt_label}.json", check.to_dict())
        if recorder:
            recorder.record_event(
                "static_check",
                "info" if check.success else "error",
                "Static Python compile check finished.",
                {"attempt": attempt_label, "success": check.success, "checked_path": check.checked_path},
            )
        if not check.success:
            command = ["python", "-m", "py_compile", str(scene_file.resolve())]
            return RenderResult(False, "", check.error, None, command)
        visual_check = run_visual_consistency_check(scene_file, plan)
        writer.write_json(project_dir, f"logs/visual_guard_{attempt_label}.json", visual_check.to_dict())
        if recorder:
            recorder.record_event(
                "visual_guard",
                "info" if visual_check.success else "error",
                "Visual consistency check finished.",
                {"attempt": attempt_label, "success": visual_check.success, "checked_path": visual_check.checked_path},
            )
        if not visual_check.success:
            command = ["visual-guard", str(scene_file.resolve())]
            return RenderResult(False, "", visual_check.error, None, command)
        media_dir = project_dir / "media"
        return await self.renderer.render(scene_file, self.settings.manim_scene_name, media_dir, quality)

    async def _render_with_repairs(
        self,
        project_dir: Path,
        scene_file: Path,
        current_code: str,
        generated: GeneratedAnimation,
        model_router: ModelRouter,
        quality: str,
        writer: ProjectManager,
        emit: ProgressCallback,
        recorder: PipelineRecorder | None = None,
    ) -> RenderResult:
        result = await self._render_checked(project_dir, scene_file, quality, writer, "0", recorder, generated.plan)
        self.renderer.save_log(project_dir / "logs" / "render_attempt_0.json", result)
        if result.success:
            emit("首次渲染成功。")
            if recorder:
                recorder.record_event("render", "info", "Initial render succeeded.", {"project_dir": project_dir})
            return result
        if result.environment_error:
            emit("本地 Manim 环境未就绪，渲染失败；已跳过模型修复。")
            if recorder:
                recorder.record_event("render", "error", "Render environment is not ready.", {"project_dir": project_dir})
            return result

        emit("首次渲染失败，开始自动修复。")
        if recorder:
            recorder.record_event("repair", "info", "Initial render failed; entering repair loop.", {"project_dir": project_dir})
        for round_index in range(1, self.settings.max_repair_rounds + 1):
            emit(f"自动修复第 {round_index} 轮：正在请求模型修复 Manim 代码。")
            repair_dir = project_dir / "repairs" / f"round_{round_index}"
            repair_dir.mkdir(parents=True, exist_ok=True)
            writer.write_text(project_dir, f"repairs/round_{round_index}/before.py", current_code)
            error_log = result.stderr + "\n" + result.stdout
            repair = await model_router.repair_code(self._repair_goal_context(generated.plan), current_code, error_log)
            emit(f"自动修复第 {round_index} 轮：模型输入与输出记录已保存。")
            current_code = repair.repaired_code
            current_code = sanitize_manim_code(current_code)
            writer.write_text(project_dir, f"repairs/round_{round_index}/after.py", current_code)
            writer.write_text(project_dir, f"repairs/round_{round_index}/notes.txt", repair.notes)
            writer.write_json(project_dir, f"repairs/round_{round_index}/summary.json", {"round": round_index, "notes": repair.notes})
            scene_file.write_text(current_code, encoding="utf-8")

            emit(f"自动修复第 {round_index} 轮：正在渲染修复后的代码。")
            result = await self._render_checked(project_dir, scene_file, quality, writer, str(round_index), recorder, generated.plan)
            self.renderer.save_log(project_dir / "logs" / f"render_attempt_{round_index}.json", result)
            if result.success:
                emit(f"自动修复第 {round_index} 轮成功。")
                if recorder:
                    recorder.record_event("repair", "info", "Repair round succeeded.", {"round": round_index})
                return result

        emit("已达到自动修复次数上限，正在渲染简化后备版本。")
        fallback = await model_router.repair_code(self._repair_goal_context(generated.plan), "Create a minimal runnable version.", "The first three repair rounds failed.")
        fallback_code = sanitize_manim_code(fallback.repaired_code)
        scene_file.write_text(fallback_code, encoding="utf-8")
        writer.write_text(project_dir, "repairs/simplified_after_failure.py", fallback_code)
        writer.write_json(project_dir, "repairs/final_repair_summary.json", {"fallback_notes": fallback.notes})
        result = await self._render_checked(project_dir, scene_file, "low", writer, "simplified", recorder, generated.plan)
        self.renderer.save_log(project_dir / "logs" / "render_simplified.json", result)
        if recorder:
            recorder.record_event("repair", "info" if result.success else "error", "Simplified fallback render finished.", {"success": result.success})
        return result

    def _repair_goal_context(self, plan: TeachingPlan) -> str:
        """Provides enough visual context for repair without resending unrelated project data."""

        scene_lines = [
            f"{scene.index}. {scene.title} | visual_plan: {scene.visual_plan} | narration: {scene.narration[:80]}"
            for scene in plan.scenes[:12]
        ]
        return "\n".join(
            [
                plan.teaching_goal,
                "",
                "Current storyboard source of truth:",
                *scene_lines,
                "",
                "Repair must preserve this storyboard and remove stale-topic or generic placeholder visuals.",
            ]
        )

    def _build_summary(self, project_dir: Path, generated: GeneratedAnimation, result: RenderResult, writer: ProjectManager) -> dict[str, object]:
        return {
            "success": result.success,
            "project_dir": str(project_dir.resolve()),
            "video_path": None,
            "output_video_path": None,
            "compose_status": "awaiting_user",
            "final_video_stale": False,
            "scene_file": str((project_dir / "scene.py").resolve()),
            "storyboard": [scene.model_dump() for scene in generated.plan.scenes],
            "manim_code": (project_dir / "scene.py").read_text(encoding="utf-8"),
            "teaching_goal": generated.plan.teaching_goal,
            "image_understanding": generated.plan.image_understanding,
            "repair_log_dir": str((project_dir / "repairs").resolve()),
            "render_log_dir": str((project_dir / "logs").resolve()),
            "ai_trace_dir": str((project_dir / "ai_traces").resolve()),
            "ai_trace_files": [str(path.resolve()) for path in sorted((project_dir / "ai_traces").glob("*.json"))],
            "failure_reason": None if result.success else (result.stderr or result.stdout)[-3000:],
        }

    async def _synthesize_narration(
        self,
        project_dir: Path,
        generated: GeneratedAnimation,
        summary: dict[str, object],
        emit: ProgressCallback,
    ) -> None:
        """Adds optional Xunfei narration without making rendering depend on TTS availability."""

        if not self.tts_service.is_configured():
            summary["tts_enabled"] = False
            summary["audio_path"] = None
            summary["tts_status"] = "disabled"
            summary["tts_message"] = "\u914d\u97f3\u672a\u542f\u7528\u3002"
            return

        emit("正在生成中文语音片段。")
        video_path_value = summary.get("video_path")
        video_path = Path(str(video_path_value)) if video_path_value else None
        result = await asyncio.to_thread(
            self.tts_service.synthesize_project_audio,
            scene_narrations=[scene.narration for scene in generated.plan.scenes],
            project_dir=project_dir,
            video_path=video_path,
        )
        summary["tts_enabled"] = result.enabled
        summary["audio_path"] = str(result.audio_path.resolve()) if result.audio_path else None
        audio_dir = project_dir / "audio"
        summary["tts_scene_audio_paths"] = [
            str(path.resolve()) for path in sorted(audio_dir.glob("scene_*.mp3")) if path.is_file() and path.stat().st_size > 0
        ]
        summary["silent_video_path"] = summary.get("video_path")
        summary["tts_status"] = result.status
        summary["tts_message"] = result.message
        if result.muxed_video_path and result.muxed_video_path.exists():
            summary["video_path"] = str(result.muxed_video_path.resolve())
            emit("配音已生成并嵌入视频。")
        elif result.error:
            summary["tts_error"] = result.error
            if result.audio_path:
                emit("配音已生成，但未能嵌入视频；已保留静音视频。")
            else:
                emit("配音生成失败，详细信息已写入 logs/tts_error.log。")

    def _write_stage_manifest(
        self,
        project_dir: Path,
        generated: GeneratedAnimation,
        summary: dict[str, object],
        writer: ProjectManager,
        total_duration_seconds: int,
    ) -> list[dict[str, object]]:
        """Creates a three-stage content plan for preview, staged rendering, and final stitching."""

        stages = self._build_stage_data(generated.plan.scenes, total_duration_seconds, bool(summary.get("segments_ready")))
        writer.write_json(project_dir, "stage_manifest.json", {"mode": "three_stage_quick_generation", "stages": stages})
        return stages

        scenes = generated.plan.scenes
        stage_titles = ["第一阶段：铺垫与建模", "第二阶段：推导与可视化", "第三阶段：拼接与总结"]
        stage_goals = [
            "生成总大纲、教学目标和开场分镜。",
            "生成核心解释分镜，并预览阶段内多个片段。",
            "完成最后总结，并在该阶段执行最终视频拼接/导出。",
        ]
        per_stage_duration = total_duration_seconds / 3
        stages: list[dict[str, object]] = []
        has_video = bool(summary.get("video_path"))
        for stage_index in range(1, 4):
            start = round((stage_index - 1) * len(scenes) / 3)
            end = round(stage_index * len(scenes) / 3)
            scene_indexes = [scene.index for scene in scenes[start:end]]
            if not scene_indexes and scenes:
                scene_indexes = [scenes[min(stage_index - 1, len(scenes) - 1)].index]
            stages.append(
                {
                    "stage": stage_index,
                    "title": stage_titles[stage_index - 1],
                    "goal": stage_goals[stage_index - 1],
                    "status": "stitched" if stage_index == 3 and has_video else ("rendered" if has_video else "planned"),
                    "scene_indexes": scene_indexes,
                    "estimated_seconds": round(per_stage_duration, 1),
                    "video_path": summary.get("video_path"),
                    "is_stitching_stage": stage_index == 3,
                }
            )
        writer.write_json(project_dir, "stage_manifest.json", {"mode": "three_stage_quick_generation", "stages": stages})
        return stages

    def _write_segment_manifest(
        self,
        project_dir: Path,
        generated: GeneratedAnimation,
        summary: dict[str, object],
        writer: ProjectManager,
        stages: list[dict[str, object]],
        segment_outputs: list[dict[str, object]] | None = None,
    ) -> None:
        """Creates a segment manifest for UI preview."""

        video_path = summary.get("video_path")
        segments = self._build_scene_segment_data(
            generated.plan.scenes,
            stages,
            segment_outputs or [],
            str(video_path) if video_path else None,
        )
        mode = "segmented_video_manifest" if segment_outputs and len(segment_outputs or []) > 1 else "single_video_segment_manifest"
        writer.write_json(project_dir, "segment_manifest.json", {"mode": mode, "segments": segments})
        return

        segments = []
        video_path = summary.get("video_path")
        segment_outputs = segment_outputs or []
        video_by_scene = {
            int(scene_index): output.get("video_path")
            for output in segment_outputs
            for scene_index in output.get("scene_indexes", [])
        }
        stage_by_scene = {
            scene_index: int(stage["stage"])
            for stage in stages
            for scene_index in stage.get("scene_indexes", [])
        }
        for scene in generated.plan.scenes:
            segments.append(
                {
                    "id": f"scene_{scene.index}",
                    "stage": stage_by_scene.get(scene.index, 1),
                    "title": scene.title,
                    "narration": scene.narration,
                    "status": "rendered" if video_path else "planned",
                    "video_path": video_by_scene.get(scene.index) or video_path,
                    "estimated_seconds": scene.estimated_seconds,
                }
            )
        mode = "segmented_video_manifest" if segment_outputs and len(segment_outputs) > 1 else "single_video_segment_manifest"
        writer.write_json(project_dir, "segment_manifest.json", {"mode": mode, "segments": segments})

    def _build_stage_data(self, scenes: list[StoryboardScene], total_duration_seconds: int, has_video: bool) -> list[dict[str, object]]:
        stage_titles = ["第一阶段：大纲与前段分镜", "第二阶段：分镜片段生成与预览", "第三阶段：拼接、配音与导出"]
        stage_goals = [
            "生成大纲、教学目标，并确定需要生成的分镜片段。",
            "按分镜逐段生成代码和视频，每个片段可独立预览。",
            "整合片段、生成分镜台词与配音，并导出最终视频。",
        ]
        per_stage_duration = total_duration_seconds / 3
        stages: list[dict[str, object]] = []
        for stage_index in range(1, 4):
            start = round((stage_index - 1) * len(scenes) / 3)
            end = round(stage_index * len(scenes) / 3)
            scene_indexes = [scene.index for scene in scenes[start:end]]
            if not scene_indexes and scenes:
                scene_indexes = [scenes[min(stage_index - 1, len(scenes) - 1)].index]
            stages.append(
                {
                    "stage": stage_index,
                    "title": stage_titles[stage_index - 1],
                    "goal": stage_goals[stage_index - 1],
                    "status": "awaiting_compose" if stage_index == 3 and has_video else ("rendered" if has_video else "planned"),
                    "scene_indexes": scene_indexes,
                    "estimated_seconds": round(per_stage_duration, 1),
                    "is_stitching_stage": stage_index == 3,
                }
            )
        return stages

    def _build_scene_segment_data(
        self,
        scenes: list[StoryboardScene],
        stages: list[dict[str, object]],
        segment_outputs: list[dict[str, object]],
        final_video_path: str | None,
    ) -> list[dict[str, object]]:
        output_by_scene = {
            int(scene_index): output
            for output in segment_outputs
            for scene_index in output.get("scene_indexes", [])
        }
        stage_by_scene = {
            scene_index: int(stage["stage"])
            for stage in stages
            for scene_index in stage.get("scene_indexes", [])
        }
        segments: list[dict[str, object]] = []
        for scene in scenes:
            output = output_by_scene.get(scene.index, {})
            video_path = output.get("video_path")
            segments.append(
                {
                    **output,
                    "id": f"scene_{scene.index}",
                    "segment_id": f"scene_{scene.index}",
                    "stage": output.get("stage") or stage_by_scene.get(scene.index, 1),
                    "segment": output.get("segment"),
                    "scene_indexes": output.get("scene_indexes") or [scene.index],
                    "title": scene.title,
                    "narration": scene.narration,
                    "narration_text": output.get("narration_text") or scene.narration,
                    "status": output.get("status") or ("rendered" if video_path else "planned"),
                    "video_path": video_path,
                    "final_video_path": final_video_path,
                    "project_dir": output.get("project_dir"),
                    "code_path": output.get("code_path"),
                    "estimated_seconds": output.get("duration") or scene.estimated_seconds,
                }
            )
        return segments

    def _stage_for_segment(self, index: int, count: int) -> int:
        if count <= 1:
            return 1
        return max(1, min(3, round(((index - 1) / max(1, count - 1)) * 2) + 1))

    def _write_live_segment_manifest(
        self,
        project_dir: Path,
        plan: TeachingPlan,
        total_duration_seconds: int,
        segment_outputs: list[dict[str, object]],
        final_video_path: Path | None,
        writer: ProjectManager,
    ) -> None:
        stages = self._build_stage_data(plan.scenes, total_duration_seconds, bool(segment_outputs))
        segments = self._build_scene_segment_data(
            plan.scenes,
            stages,
            segment_outputs,
            str(final_video_path.resolve()) if final_video_path else None,
        )
        writer.write_json(project_dir, "stage_manifest.json", {"mode": "three_stage_quick_generation", "stages": stages})
        writer.write_json(project_dir, "segment_manifest.json", {"mode": "live_segment_manifest", "segments": segments})

    def _build_partial_result(
        self,
        project_dir: Path,
        plan: TeachingPlan,
        total_duration_seconds: int,
        segment_outputs: list[dict[str, object]],
        final_video_path: Path | None,
    ) -> dict[str, object]:
        stages = self._build_stage_data(plan.scenes, total_duration_seconds, bool(segment_outputs))
        segments = self._build_scene_segment_data(
            plan.scenes,
            stages,
            segment_outputs,
            str(final_video_path.resolve()) if final_video_path else None,
        )
        return {
            "project_dir": str(project_dir.resolve()),
            "storyboard": [scene.model_dump() for scene in plan.scenes],
            "stages": stages,
            "segments": segments,
            "video_path": str(final_video_path.resolve()) if final_video_path else None,
        }

    def _load_stage_manifest(self, project_dir: Path) -> list[dict[str, object]]:
        manifest_path = project_dir / "stage_manifest.json"
        if not manifest_path.exists():
            return []
        import json

        return json.loads(manifest_path.read_text(encoding="utf-8")).get("stages", [])

    def _load_segment_manifest(self, project_dir: Path) -> list[dict[str, object]]:
        manifest_path = project_dir / "segment_manifest.json"
        if not manifest_path.exists():
            return []
        import json

        return json.loads(manifest_path.read_text(encoding="utf-8")).get("segments", [])
