import asyncio

from backend.ai.schemas import GeneratedAnimation, RepairResult, StoryboardScene, TeachingPlan
from backend.core.config import Settings
from backend.rendering.manim_renderer import RenderResult
from backend.services.generation_service import GenerationService
from backend.services.project_manager import ProjectManager


def test_repair_loop_continues_beyond_old_three_round_limit(tmp_path):
    settings = Settings(generated_projects_dir=tmp_path / "projects")
    manager = ProjectManager(settings.generated_projects_dir)
    service = GenerationService(settings, manager)
    project_dir = manager.create_project()
    scene_file = manager.write_text(project_dir, "scene.py", "from manim import *\n")
    plan = TeachingPlan(
        image_understanding="无图片。",
        teaching_goal="测试无限修复。",
        conflict_strategy="提示词优先。",
        scenes=[StoryboardScene(index=1, title="测试", narration="测试", visual_plan="显示文字")],
        code_plan="保持简单。",
    )
    generated = GeneratedAnimation(plan=plan, manim_code=scene_file.read_text(encoding="utf-8"))
    render_calls = 0

    async def fake_render(*_args, **_kwargs):
        nonlocal render_calls
        render_calls += 1
        if render_calls >= 6:
            return RenderResult(True, "", "", project_dir / "success.mp4", [])
        return RenderResult(False, "", "code error", None, [])

    class Router:
        calls = 0

        async def repair_code(self, *_args):
            self.calls += 1
            return RepairResult(
                repaired_code="from manim import *\nclass GeneratedTeachingScene(Scene):\n    def construct(self):\n        pass\n",
                notes=f"repair {self.calls}",
            )

    router = Router()
    service._render_checked = fake_render
    service.renderer.save_log = lambda *_args, **_kwargs: None

    result = asyncio.run(
        service._render_with_repairs(
            project_dir,
            scene_file,
            generated.manim_code,
            generated,
            router,
            "low",
            manager,
            lambda _message: None,
        )
    )

    assert result.success
    assert router.calls == 5
    assert render_calls == 6
