import ast
from pathlib import Path

from backend.ai.model_config import ModelRequestConfig
from backend.ai.model_router import ModelRouter
from backend.ai.schemas import StoryboardScene, TeachingPlan
from backend.rendering.code_sanitizer import sanitize_manim_code
from backend.rendering.visual_guard import run_visual_consistency_check


def make_plan(*, goal: str, title: str, narration: str, visual_plan: str) -> TeachingPlan:
    return TeachingPlan(
        image_understanding="无图片",
        teaching_goal=goal,
        conflict_strategy="提示词优先",
        scenes=[
            StoryboardScene(
                index=1,
                title=title,
                narration=narration,
                visual_plan=visual_plan,
                estimated_seconds=20,
            )
        ],
        code_plan=visual_plan,
    )


def test_recovers_complete_fenced_manim_code_from_truncated_reasoning():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    code = (
        "from manim import *\n\n"
        "class GeneratedTeachingScene(Scene):\n"
        "    def construct(self):\n"
        "        self.play(Create(Circle()))\n"
    )
    data = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {
                    "content": '{"manim_code":"from manim import',
                    "reasoning_content": f"analysis\n```python\n{code}```\nmore analysis",
                },
            }
        ]
    }

    result = router._parse_code_generation_result(data)

    assert result.manim_code == code.strip()
    ast.parse(result.manim_code)


def test_vibration_fallback_uses_mass_spring_not_railway_section():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    plan = make_plan(
        goal="解释机械振动与固有频率",
        title="振动分析",
        narration="质量矩阵和刚度矩阵决定系统固有频率。",
        visual_plan="展示两个质量块由弹簧连接，并显示振型位移箭头。",
    )

    code = router._generic_code_from_storyboard(plan, 20)

    assert "mass_spring_view" in code
    assert "railway_section" not in code
    assert "钢轨" not in code
    assert "轨枕" not in code
    assert "每一段都按 visual_plan 重新构图" not in code
    assert plan.scenes[0].narration not in code
    assert plan.scenes[0].visual_plan not in code
    ast.parse(code)


def test_geography_fallback_does_not_render_internal_prompt_text():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    plan = make_plan(
        goal="解释朝鲜半岛的地理与历史",
        title="朝鲜半岛的位置",
        narration="朝鲜半岛东临日本海，西临黄海。",
        visual_plan="绘制半岛轮廓并标出周边海域和北方边界。",
    )

    code = router._generic_code_from_storyboard(plan, 20)

    assert "geography_view" in code
    assert "beat_note" not in code
    assert "beat_visual" not in code
    assert "分镜驱动生成" not in code
    assert plan.scenes[0].visual_plan not in code
    ast.parse(code)


def test_visual_guard_rejects_internal_banner_and_cross_topic_railway_assets(tmp_path: Path):
    plan = make_plan(
        goal="解释机械振动",
        title="固有频率",
        narration="质量块由弹簧连接。",
        visual_plan="绘制质量块和弹簧。",
    )
    banner_file = tmp_path / "banner.py"
    banner_file.write_text(
        'from manim import *\nText("分镜驱动生成：每一段都按 visual_plan 重新构图")\n',
        encoding="utf-8",
    )
    railway_file = tmp_path / "railway.py"
    railway_file.write_text('from manim import *\nText("轨枕、道床、路基")\n', encoding="utf-8")

    banner_result = run_visual_consistency_check(banner_file, plan)
    railway_result = run_visual_consistency_check(railway_file, plan)

    assert not banner_result.success
    assert "内部 fallback" in banner_result.error
    assert not railway_result.success
    assert "铁路专用视觉素材" in railway_result.error


def test_legacy_placeholder_template_is_blocked_and_banner_is_sanitized(tmp_path: Path):
    plan = make_plan(
        goal="解释冒险故事",
        title="旅途开始",
        narration="旅行者踏上新的旅途。",
        visual_plan="绘制人物沿曲线路径前进。",
    )
    legacy_code = (
        'from manim import *\n'
        'subtitle = Text("分镜驱动生成：每一段都按 visual_plan 重新构图")\n'
        'beat_note = Text("旁白原文")\n'
        'beat_visual = Text("视觉计划原文")\n'
        'def relation_flow(labels):\n'
        '    return VGroup()\n'
    )
    scene_file = tmp_path / "legacy_placeholder.py"
    scene_file.write_text(legacy_code, encoding="utf-8")

    result = run_visual_consistency_check(scene_file, plan)
    sanitized = sanitize_manim_code(legacy_code)
    scene_file.write_text(sanitized, encoding="utf-8")
    sanitized_result = run_visual_consistency_check(scene_file, plan)

    assert not result.success
    assert "内部 fallback" in result.error or "永久禁用" in result.error
    assert "分镜驱动生成：每一段都按 visual_plan 重新构图" not in sanitized
    assert not sanitized_result.success
    assert "永久禁用" in sanitized_result.error
