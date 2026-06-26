from dataclasses import asdict, dataclass
from pathlib import Path

from backend.ai.schemas import TeachingPlan


@dataclass
class VisualGuardResult:
    """Checks whether generated visuals still match the current teaching plan."""

    success: bool
    error: str
    checked_path: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


STALE_TOPIC_TERMS = [
    "沈阳",
    "盛京",
    "北陵",
    "Bilibili",
    "bilibili",
    "弹幕",
    "UP主",
    "悬索桥",
    "主缆",
    "吊索",
    "桥塔",
]

MATH_VISUAL_MARKERS = [
    "NumberPlane",
    "Axes(",
    "axis_x",
    "axis_y",
    "vec = Arrow",
    "v = x i + y j",
    "投影",
    "向量",
]

MATH_PLAN_TERMS = [
    "数学",
    "向量",
    "矩阵",
    "函数",
    "坐标",
    "公式",
    "方程",
    "投影",
    "物理",
    "力",
]

BRIDGE_PLAN_TERMS = [
    "斜拉桥",
    "斜拉索",
    "索力",
    "桥塔",
    "主梁",
    "桥面",
    "cable-stayed",
    "stay cable",
]

GENERIC_VISUAL_MARKERS = [
    "generic_board",
    "core_region",
    "idea_cards",
    "当前主题驱动的分镜可视化",
]


def run_visual_consistency_check(scene_file: Path, plan: TeachingPlan) -> VisualGuardResult:
    """Blocks obvious stale-topic assets before spending time rendering them."""

    code = scene_file.read_text(encoding="utf-8", errors="ignore")
    plan_text = _plan_text(plan)

    stale_terms = [term for term in STALE_TOPIC_TERMS if term in code and term.lower() not in plan_text.lower()]
    if stale_terms:
        return VisualGuardResult(
            False,
            "生成代码包含当前教学计划中没有出现的旧主题素材或标签: " + ", ".join(stale_terms),
            str(scene_file.resolve()),
        )

    has_math_visual = any(marker in code for marker in MATH_VISUAL_MARKERS)
    plan_allows_math = any(term in plan_text for term in MATH_PLAN_TERMS)
    if has_math_visual and not plan_allows_math:
        return VisualGuardResult(
            False,
            "当前主题不是数学/坐标/向量类内容，但生成代码包含坐标轴或向量投影类占位图示。",
            str(scene_file.resolve()),
        )

    generic_markers = [marker for marker in GENERIC_VISUAL_MARKERS if marker in code]
    if generic_markers:
        return VisualGuardResult(
            False,
            "生成代码仍包含通用占位视觉层，必须删除并按每个分镜 visual_plan 绘制具体对象与动作: " + ", ".join(generic_markers),
            str(scene_file.resolve()),
        )

    has_bridge_plan = any(term.lower() in plan_text.lower() for term in BRIDGE_PLAN_TERMS)
    has_generic_visual = any(marker in code for marker in GENERIC_VISUAL_MARKERS)
    if has_bridge_plan and has_generic_visual:
        return VisualGuardResult(
            False,
            "斜拉桥/斜拉索主题不能使用 generic_board/core_region/idea_cards 这类通用抽象占位图；必须绘制桥塔、主梁、斜拉索、荷载与索力路径。",
            str(scene_file.resolve()),
        )

    return VisualGuardResult(True, "", str(scene_file.resolve()))


def _plan_text(plan: TeachingPlan) -> str:
    return "\n".join(
        [plan.teaching_goal, plan.code_plan, plan.image_understanding]
        + [f"{scene.title}\n{scene.narration}\n{scene.visual_plan}" for scene in plan.scenes]
    )
