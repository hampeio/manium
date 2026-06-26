from backend.ai.model_config import resolve_model_config
from backend.ai.model_config import ModelRequestConfig
from backend.ai.model_router import ModelRouter
from backend.ai.schemas import GenerationStrategy, StoryboardBatchSpec, StoryboardScene, TeachingPlan
from backend.core.config import Settings
from backend.pipeline.recorder import PipelineRecorder
from backend.rendering.static_checker import run_static_check
from backend.rendering.visual_guard import run_visual_consistency_check
from backend.services.subtitle_service import build_subtitles
import httpx
import json
import pytest


def test_mock_generation_builds_required_artifacts():
    settings = Settings(default_provider="mock")
    config = resolve_model_config(settings, None, None, None, None)
    router = ModelRouter(config)
    generated = router._mock_animation("解释向量投影", "", "仅提供提示词")
    srt, timeline = build_subtitles(generated.plan.scenes)

    assert "GeneratedTeachingScene" in generated.manim_code
    assert len(generated.plan.scenes) >= 3
    assert ".srt" not in srt
    assert timeline[0]["start"] == 0


def test_teaching_plan_accepts_five_medium_grain_scenes():
    scenes = [
        StoryboardScene(index=index, title=f"分镜 {index}", narration="中文旁白", visual_plan="图形演示", estimated_seconds=20)
        for index in range(1, 6)
    ]
    plan = TeachingPlan(
        image_understanding="无图片输入。",
        teaching_goal="解释悬索桥。",
        conflict_strategy="提示词优先。",
        scenes=scenes,
        code_plan="使用桥塔、主缆、吊索和荷载箭头。",
    )

    assert len(plan.scenes) == 5


@pytest.mark.anyio
async def test_segment_code_generation_falls_back_on_dns_failure():
    settings = Settings(default_provider="deepseek", deepseek_api_key="test-key")
    config = resolve_model_config(settings, "deepseek", "test-key", "https://example.invalid/v1", "deepseek-test")
    router = ModelRouter(config)

    async def fail_chat(*_args, **_kwargs):
        raise httpx.ConnectError("[Errno 11001] getaddrinfo failed")

    router._chat_json = fail_chat
    scenes = [
        StoryboardScene(index=index, title=f"分镜 {index}", narration="中文旁白", visual_plan="图形演示", estimated_seconds=20)
        for index in range(1, 4)
    ]
    plan = TeachingPlan(
        image_understanding="无图片输入。",
        teaching_goal="解释悬索桥。",
        conflict_strategy="提示词优先。",
        scenes=scenes,
        code_plan="使用桥塔、主缆、吊索和荷载箭头。",
    )

    code = await router.generate_code_for_segment(plan, segment_index=3, segment_count=3, segment_duration_seconds=60)

    assert "GeneratedTeachingScene" in code
    assert "from manim import *" in code


def test_bilibili_fallback_uses_storyboard_compiler_not_topic_template():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    scenes = [
        StoryboardScene(index=1, title="Bilibili origin", narration="Bilibili grows from ACG to a video platform.", visual_plan="show timeline", estimated_seconds=20),
        StoryboardScene(index=2, title="Danmaku", narration="弹幕 makes watching feel shared.", visual_plan="danmaku flies across player", estimated_seconds=20),
        StoryboardScene(index=3, title="UP creator", narration="UP主 creates content.", visual_plan="creator connects to categories", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="No image.",
        teaching_goal="Explain Bilibili, danmaku, UP creators, and community culture.",
        conflict_strategy="Prompt first.",
        scenes=scenes,
        code_plan="video player, danmaku, UP creator, categories, timeline",
    )

    code = router._code_from_storyboard(plan, 300)

    assert "relation_flow" in code
    assert "layered_section" in code
    assert "player =" not in code
    assert "category_cards" not in code
    assert "generic_board" not in code
    assert "NumberPlane" not in code
    assert "vec = Arrow" not in code


def test_city_fallback_uses_storyboard_compiler_not_city_template():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    scenes = [
        StoryboardScene(index=1, title="Shenyang location", narration="Introduce Shenyang as a city in Liaoning.", visual_plan="map card and city dot", estimated_seconds=20),
        StoryboardScene(index=2, title="History and culture", narration="Explain Qing history and the palace culture.", visual_plan="timeline and palace", estimated_seconds=20),
        StoryboardScene(index=3, title="Industry and tourism", narration="Show industry transformation and tourist landmarks.", visual_plan="factory and landmark cards", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="No image.",
        teaching_goal="Introduce Shenyang city history, industry, culture, and tourism.",
        conflict_strategy="Prompt first.",
        scenes=scenes,
        code_plan="city map, history timeline, palace, industry, tourism landmark cards",
    )

    code = router._code_from_storyboard(plan, 300)

    assert "generic_board" not in code
    assert "city_hub" not in code
    assert "palace_group" not in code
    assert "industry_group" not in code
    assert "attraction_cards" not in code
    assert "relation_flow" in code
    assert "NumberPlane" not in code
    assert "vec = Arrow" not in code


def test_country_fallback_does_not_reuse_shenyang_city_assets():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    scenes = [
        StoryboardScene(index=1, title="China geography", narration="China is in East Asia.", visual_plan="show China map and Beijing", estimated_seconds=20),
        StoryboardScene(index=2, title="Flag and capital", narration="The capital is Beijing.", visual_plan="show national flag", estimated_seconds=20),
        StoryboardScene(index=3, title="Great Wall culture", narration="Great Wall and inventions represent history.", visual_plan="show culture cards", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="No image.",
        teaching_goal="Introduce China geography, history, culture, and modern development.",
        conflict_strategy="Prompt first.",
        scenes=scenes,
        code_plan="China country overview, Beijing, Great Wall, culture, economy, technology",
    )

    code = router._code_from_storyboard(plan, 300)

    assert "generic_board" not in code
    assert "country_map" not in code
    assert "city_hub" not in code
    assert "\\u6c88\\u9633" not in code
    assert "category_cards" not in code
    assert "relation_flow" in code
    assert "axis_x" not in code
    assert "axis_y" not in code


def test_static_checker_catches_generated_python_syntax_error(tmp_path):
    scene_file = tmp_path / "scene.py"
    scene_file.write_text("from manim import *\n\nclass GeneratedTeachingScene(Scene):\n    def construct(self):\n        Text('broken'\n", encoding="utf-8")

    result = run_static_check(scene_file)

    assert not result.success
    assert "SyntaxError" in result.error
    assert str(scene_file.resolve()) == result.checked_path


def test_local_storyboard_fallback_is_topic_grounded_for_rail_fasteners():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    strategy = GenerationStrategy(
        image_understanding="无图片。",
        teaching_goal="用中文教学动画介绍轨道扣件是什么。",
        conflict_strategy="提示词优先。",
        target_duration_seconds=300,
        estimated_scene_count=15,
        ai_call_count=5,
        batches=[
            StoryboardBatchSpec(batch_index=1, stage=1, title="第一阶段", goal="介绍轨道扣件结构", scene_count=5, duration_seconds=100),
            StoryboardBatchSpec(batch_index=2, stage=2, title="第二阶段", goal="解释轨道扣件受力", scene_count=5, duration_seconds=100),
            StoryboardBatchSpec(batch_index=3, stage=3, title="第三阶段", goal="总结轨道扣件维护", scene_count=5, duration_seconds=100),
        ],
        code_plan="扣件剖面图、弹条、螺栓、钢轨、轨枕。",
    )

    result = router._mock_storyboard_batch(strategy, strategy.batches[0], 1)
    joined = "\n".join(f"{scene.title}\n{scene.narration}\n{scene.visual_plan}" for scene in result.scenes)

    assert "扣件" in joined
    assert "弹条" in joined
    assert "钢轨" in joined
    assert "提出问题" not in joined
    assert "公式连接" not in joined
    assert "坐标" not in joined


def test_visual_guard_blocks_stale_city_assets_for_country_plan(tmp_path):
    scenes = [
        StoryboardScene(index=1, title="中国地理", narration="介绍中国的位置。", visual_plan="显示中国主题区域。", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="无图片。",
        teaching_goal="介绍中国。",
        conflict_strategy="提示词优先。",
        scenes=scenes,
        code_plan="中国主题图解。",
    )
    scene_file = tmp_path / "scene.py"
    scene_file.write_text("from manim import *\nlabel = Text('沈阳')\n", encoding="utf-8")

    result = run_visual_consistency_check(scene_file, plan)

    assert not result.success
    assert "旧主题素材" in result.error


def test_visual_guard_blocks_math_placeholder_for_non_math_plan(tmp_path):
    scenes = [
        StoryboardScene(index=1, title="中国地理", narration="介绍中国的位置。", visual_plan="显示中国主题区域。", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="无图片。",
        teaching_goal="介绍中国。",
        conflict_strategy="提示词优先。",
        scenes=scenes,
        code_plan="中国主题图解。",
    )
    scene_file = tmp_path / "scene.py"
    scene_file.write_text("from manim import *\nplane = NumberPlane()\n", encoding="utf-8")

    result = run_visual_consistency_check(scene_file, plan)

    assert not result.success
    assert "坐标轴" in result.error


def test_pipeline_recorder_writes_manifest_and_events(tmp_path):
    recorder = PipelineRecorder(tmp_path)
    recorder.record_problem_frame(
        user_prompt="介绍中国",
        has_image=False,
        priority_rule="Only prompt is provided.",
        target_duration_seconds=300,
        quality="low",
        compact_timing=True,
    )
    recorder.start_stage("outline", "Start outline.")
    recorder.complete_stage("outline", "Outline done.", {"ai_call_count": 3})
    recorder.finish()

    manifest = json.loads((tmp_path / "pipeline_manifest.json").read_text(encoding="utf-8"))
    events = (tmp_path / "pipeline_events.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert manifest["stages"][0]["stage"] == "outline"
    assert manifest["stages"][0]["status"] == "completed"
    assert (tmp_path / "problem_frame.json").exists()
    assert len(events) >= 4


def test_mojibake_question_marks_do_not_trigger_bilibili_template():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    scenes = [
        StoryboardScene(index=1, title="????", narration="????", visual_plan="????", estimated_seconds=20),
        StoryboardScene(index=2, title="????", narration="????", visual_plan="????", estimated_seconds=20),
        StoryboardScene(index=3, title="????", narration="????", visual_plan="????", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="No image.",
        teaching_goal="????????",
        conflict_strategy="Prompt first.",
        scenes=scenes,
        code_plan="????????",
    )

    code = router._code_from_storyboard(plan, 300)

    assert "category_cards" not in code
    assert "generic_board" not in code
    assert "relation_flow" in code


def test_cable_stayed_bridge_fallback_uses_storyboard_compiler():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    scenes = [
        StoryboardScene(
            index=1,
            title="斜拉桥三要素",
            narration="介绍桥塔、主梁和斜拉索如何组成稳定体系。",
            visual_plan="绘制桥塔、主梁和多根斜拉索，并标出关键构件。",
            estimated_seconds=20,
        ),
        StoryboardScene(
            index=2,
            title="索力分解",
            narration="说明斜拉索拉力可以分解为水平分力和竖向分力。",
            visual_plan="画出索力 T、水平分力和竖向分力箭头。",
            estimated_seconds=20,
        ),
        StoryboardScene(
            index=3,
            title="荷载传递路径",
            narration="车辆荷载经主梁传给斜拉索，再传给桥塔。",
            visual_plan="用箭头展示荷载、索力和桥塔受压路径。",
            estimated_seconds=20,
        ),
    ]
    plan = TeachingPlan(
        image_understanding="无图片输入。",
        teaching_goal="解释斜拉索在斜拉桥中的作用。",
        conflict_strategy="提示词优先。",
        scenes=scenes,
        code_plan="必须绘制桥塔、主梁、斜拉索、荷载箭头和索力分解。",
    )

    code = router._code_from_storyboard(plan, 300)

    assert "force_path" in code
    assert "relation_flow" in code
    assert "stay_cables" not in code
    assert "bridge_base" not in code
    assert "generic_board" not in code
    assert "core_region" not in code
    assert "NumberPlane" not in code


def test_railway_ballast_storyboard_compiles_to_visual_skills():
    router = ModelRouter(ModelRequestConfig(provider="mock", api_key=None, base_url="", model=""))
    scenes = [
        StoryboardScene(
            index=1,
            title="铁路路基道床组成",
            narration="介绍钢轨、轨枕、道床和路基的上下关系。",
            visual_plan="屏幕中央显示铁路断面分层：路基、梯形道床、轨枕、两条钢轨，并用中文标签标注。",
            estimated_seconds=20,
        ),
        StoryboardScene(
            index=2,
            title="荷载扩散",
            narration="轮载经钢轨和轨枕传入道床，再扩散到路基。",
            visual_plan="用红色向下箭头表示轮载，用黄色分散箭头穿过道床显示应力扩散。",
            estimated_seconds=20,
        ),
        StoryboardScene(
            index=3,
            title="捣固与整形",
            narration="施工机具压实道砟颗粒，恢复道床断面。",
            visual_plan="显示捣固机具从上方下压，捣固杆进入道床，颗粒变密实。",
            estimated_seconds=20,
        ),
    ]
    plan = TeachingPlan(
        image_understanding="无图片输入。",
        teaching_goal="介绍铁路路基道床的组成、功能和施工要点。",
        conflict_strategy="提示词优先。",
        scenes=scenes,
        code_plan="严格按照每个分镜的 visual_plan 生成断面、荷载和施工机具。",
    )

    code = router._code_from_storyboard(plan, 300)

    assert "layered_section" in code
    assert "force_path" in code
    assert "construction_machine" in code
    assert "ballast_particles" in code
    assert "generic_board" not in code
    assert "core_region" not in code


def test_visual_guard_blocks_generic_board_for_cable_stayed_bridge(tmp_path):
    scene_file = tmp_path / "scene.py"
    scene_file.write_text(
        "from manim import *\n"
        "class GeneratedTeachingScene(Scene):\n"
        "    def construct(self):\n"
        "        generic_board = VGroup()\n"
        "        core_region = Rectangle()\n",
        encoding="utf-8",
    )
    plan = TeachingPlan(
        image_understanding="无图片输入。",
        teaching_goal="解释斜拉索在斜拉桥中的作用。",
        conflict_strategy="提示词优先。",
        scenes=[
            StoryboardScene(
                index=1,
                title="索力路径",
                narration="车辆荷载通过斜拉索传给桥塔。",
                visual_plan="必须绘制桥塔、主梁和斜拉索。",
                estimated_seconds=20,
            )
        ],
        code_plan="桥塔、主梁、斜拉索、荷载箭头。",
    )

    result = run_visual_consistency_check(scene_file, plan)

    assert not result.success
    assert "generic_board" in result.error


@pytest.mark.anyio
async def test_city_segment_generation_uses_local_template_without_ai_call():
    settings = Settings(default_provider="deepseek", deepseek_api_key="test-key")
    config = resolve_model_config(settings, "deepseek", "test-key", "https://example.invalid/v1", "deepseek-test")
    router = ModelRouter(config)

    async def fail_chat(*_args, **_kwargs):
        raise httpx.ConnectError("[Errno 11001] getaddrinfo failed")

    router._chat_json = fail_chat
    scenes = [
        StoryboardScene(index=1, title="City location", narration="Locate Shenyang.", visual_plan="map card", estimated_seconds=20),
        StoryboardScene(index=2, title="Tourism", narration="Show tourist landmarks.", visual_plan="landmark cards", estimated_seconds=20),
        StoryboardScene(index=3, title="Industry", narration="Show manufacturing transformation.", visual_plan="factory silhouette", estimated_seconds=20),
    ]
    plan = TeachingPlan(
        image_understanding="No image.",
        teaching_goal="Explain Shenyang city tourism and industry.",
        conflict_strategy="Prompt first.",
        scenes=scenes,
        code_plan="city map, tourism landmarks, industry",
    )

    code = await router.generate_code_for_segment(plan, segment_index=1, segment_count=3, segment_duration_seconds=60)

    assert "GeneratedTeachingScene" in code
    assert "generic_board" not in code
    assert "city_hub" not in code
    assert "relation_flow" in code
    assert "NumberPlane" not in code
