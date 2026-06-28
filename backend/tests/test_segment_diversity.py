from backend.rendering.visual_guard import run_segment_diversity_check


def test_blocks_placeholder_end_card():
    result = run_segment_diversity_check(
        "from manim import *\nText('分镜演示完成')",
        [],
    )

    assert not result.success
    assert "占位" in result.error


def test_blocks_same_visual_program_with_new_labels():
    first = """
from manim import *
class GeneratedTeachingScene(Scene):
    def construct(self):
        title = Text("第一段")
        boxes = VGroup(*[Rectangle() for _ in range(8)]).arrange(RIGHT)
        arrows = VGroup(*[Arrow(LEFT, RIGHT) for _ in range(8)])
        self.play(Write(title))
        self.play(LaggedStart(*[Create(box) for box in boxes]))
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in arrows]))
        self.wait(1)
"""
    second = first.replace("第一段", "完全不同的标题")

    result = run_segment_diversity_check(second, [first])

    assert not result.success
    assert result.compared_segment == 1
    assert result.similarity >= 0.94


def test_allows_distinct_visual_program():
    first = """
from manim import *
class GeneratedTeachingScene(Scene):
    def construct(self):
        boxes = VGroup(*[Rectangle() for _ in range(12)])
        arrows = VGroup(*[Arrow(LEFT, RIGHT) for _ in range(12)])
        self.play(LaggedStart(*[Create(box) for box in boxes]))
        self.play(LaggedStart(*[GrowArrow(arrow) for arrow in arrows]))
"""
    second = """
from manim import *
class GeneratedTeachingScene(Scene):
    def construct(self):
        tracker = ValueTracker(0)
        curve = always_redraw(lambda: ParametricFunction(lambda t: [t, tracker.get_value(), 0]))
        dots = VGroup(*[Dot() for _ in range(12)])
        self.add(curve, dots)
        self.play(tracker.animate.set_value(2))
        self.play(Rotate(curve, PI / 2))
        self.play(FadeOut(curve), FadeOut(dots))
"""

    result = run_segment_diversity_check(second, [first])

    assert result.success
