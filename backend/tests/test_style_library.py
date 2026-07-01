import json
import asyncio

from backend.ai.model_config import ModelRequestConfig
from backend.ai.model_router import ModelRouter
from backend.services.style_library_service import StyleLibraryService


SAMPLE = b"""
from manim import *

class Derivation(MovingCameraScene):
    def construct(self):
        title = Text("Projection", font="Arial", font_size=42, color=BLUE)
        eq1 = MathTex(r"a+b=c", color=WHITE)
        eq2 = MathTex(r"a=c-b", color=YELLOW)
        group = VGroup(title, eq1).arrange(DOWN)
        self.play(Write(title), Create(eq1), run_time=1.2)
        self.play(ReplacementTransform(eq1, eq2), run_time=0.8)
        self.play(self.camera.frame.animate.scale(0.8))
        self.wait(0.5)
"""


def test_analyze_and_version_style(tmp_path):
    service = StyleLibraryService(tmp_path / "styles")
    style = service.analyze(style_name="推导风格", files=[("scene.py", SAMPLE)])
    assert style["active_version"] == 1
    assert style["analysis"]["code_structure"]["scene_count"] == 1
    assert style["analysis"]["code_structure"]["animations"]["Write"] >= 1
    assert "推导风格" in style["preset"]["prompt_preset"]

    updated = service.save_preset(style["id"], {"animation_speed": "快速"})
    assert updated["active_version"] == 2
    assert len(updated["versions"]) == 2

    rolled_back = service.rollback(style["id"], 1)
    assert rolled_back["active_version"] == 1

    exported = json.loads((tmp_path / "styles" / "styles.json").read_text(encoding="utf-8"))
    assert exported["styles"][0]["id"] == style["id"]


def test_model_api_style_analysis_and_merge(tmp_path):
    router = ModelRouter(ModelRequestConfig(provider="openai-compatible", api_key="test", base_url="https://example.invalid/v1", model="style-model"))

    async def fake_chat(*_args, **_kwargs):
        return {"choices": [{"message": {"content": json.dumps({
            "style_name": "AI 推导风格",
            "style_description": "模型归纳描述",
            "visual_style": {"layout": "board"},
            "teaching_rhythm": {"mode": "reveal"},
            "code_patterns": {"transform": True},
            "prompt_preset": "严格使用逐步公式推导与一致配色。",
            "recommended_scene_count": 6,
            "animation_speed": "中等",
            "palette": ["#000000", "#58C4DD"],
            "fonts": ["Arial"],
            "confidence": 0.9,
            "inference_notes": [],
        }, ensure_ascii=False)}}]}

    router._chat_json = fake_chat
    result = asyncio.run(router.analyze_manim_style({"code_structure": {}}))
    service = StyleLibraryService(tmp_path / "styles")
    style = service.analyze(style_name="原始风格", files=[("scene.py", SAMPLE)])
    merged = service.apply_model_analysis(style["id"], result, router.config.model)
    assert merged["name"] == "AI 推导风格"
    assert merged["preset"]["scene_count"] == 6
    assert merged["analysis"]["analysis_method"] == "local-evidence+model-api"

