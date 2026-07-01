import json
from pathlib import Path
from typing import Any

import backend.ai.model_router as model_router
import backend.ai.prompts as prompts


PROMPT_NAMES = [
    "SYSTEM_PROMPT",
    "PLAN_AND_CODE_PROMPT",
    "GENERATION_STRATEGY_PROMPT",
    "STORYBOARD_BATCH_PROMPT",
    "CODE_FROM_PLAN_PROMPT",
    "SEGMENT_CODE_PROMPT",
    "REPAIR_PROMPT",
]

OVERRIDE_PATH = Path("prompt_overrides.json")

GENERAL_VISUAL_CORRECTNESS_RULES = """

视觉与事实正确性硬性规则：
1. 在写代码前，先从当前教学内容提取必须成立的事实约束，包括对象类别、组成关系、连接拓扑、相对位置、方向、顺序、尺度关系、运动规律和因果关系。画面美观不能凌驾于事实正确性。
2. 对工程结构、机械装置、物理过程、几何图形、地图、流程和数据图表，先建立一个简短的“可验证模型”，再创建 Manim 对象。不得仅凭名称套用看似相近的通用图形。
3. 所有关联对象必须共享同一份几何或数据来源。例如：曲线及其连接点使用同一个函数；节点和连线使用同一组坐标；标签、箭头和高亮绑定实际对象位置；不得分别凭目测计算而造成断开、穿透、反向或错位。
4. 优先使用方向明确、可检查的表达方式。曲线优先使用显式函数、参数方程或明确控制点；路径和箭头必须核对起点、终点及方向。若某个 API 的正负号、角度方向或坐标含义容易混淆，不得猜测，应改用更明确的基础对象或显式点列。
5. 创建代码前先列出关键不变量，返回前逐项验证。例如：上方对象的 y 值确实更大；连接端点重合；包含关系成立；运动前后顺序正确；受力箭头方向符合定义；曲线的极值、凹凸和端点符合教学事实。
6. 区分“示意性简化”和“事实性错误”。可以省略次要细节，但不得改变对象类型、核心构造、拓扑关系、方向、数量级或工作原理。若必须简化，应保持最具辨识度且决定原理的结构特征。
7. 不得把相似概念混画。例如，不得因外观相似而混用不同桥型、不同机构、不同电路拓扑、不同流程方向、不同图表语义或不同数学对象。先根据当前主题确定类别，再选择视觉语法。
8. 对称对象应由同一组参数镜像生成；重复构件应由统一规则生成；连续对象与附着对象应从主对象采样位置。避免为左右两侧或相关构件各写一套不一致的魔法数字。
9. 画面生成后进行一次内部视觉审查：检查对象是否连接、遮挡、越界、倒置、反向、比例失真或与旁白矛盾。若发现风险，先修正代码再返回，不要依赖后续自动修复。
10. 自动修复时不仅修复语法和渲染错误，还必须重新检查上述事实、几何与拓扑不变量；不得在修复 API 时保留已经识别出的错误结构。
11. 当输入不足以确定专业细节时，使用保守、标准、可解释的示意模型，并避免展示未经确认的具体构造；不得用自信但错误的细节填补信息缺口。
12. 最终代码必须同时满足：可运行、与分镜一致、事实关系正确、相关对象几何一致。任何一项不满足都不能视为完成。
"""


def get_prompt_values() -> dict[str, str]:
    """Return the currently active prompt templates."""

    return {name: str(getattr(prompts, name)) for name in PROMPT_NAMES}


def load_prompt_overrides(path: Path = OVERRIDE_PATH) -> dict[str, str]:
    """Load saved prompt overrides and apply them to prompt modules."""

    if not path.exists():
        _ensure_general_visual_correctness_rules()
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    values = raw.get("prompts", raw) if isinstance(raw, dict) else {}
    updates = {
        name: str(values[name])
        for name in PROMPT_NAMES
        if name in values
        and str(values[name]).strip()
        and not _is_legacy_english_prompt(str(values[name]))
    }
    apply_prompt_overrides(updates, save=False, path=path)
    _ensure_general_visual_correctness_rules()
    return updates


def apply_prompt_overrides(updates: dict[str, Any], *, save: bool = True, path: Path = OVERRIDE_PATH) -> dict[str, str]:
    """Apply editable prompt templates at runtime and optionally persist them."""

    clean_updates = {
        name: str(value)
        for name, value in updates.items()
        if name in PROMPT_NAMES and isinstance(value, str) and value.strip()
    }
    for name, value in clean_updates.items():
        setattr(prompts, name, value)
        if hasattr(model_router, name):
            setattr(model_router, name, value)
    _ensure_general_visual_correctness_rules()

    if save:
        path.write_text(json.dumps({"prompts": get_prompt_values()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_prompt_values()


def _ensure_general_visual_correctness_rules() -> None:
    marker = "视觉与事实正确性硬性规则："
    current = str(prompts.SYSTEM_PROMPT)
    if marker not in current:
        current = current.rstrip() + GENERAL_VISUAL_CORRECTNESS_RULES
        prompts.SYSTEM_PROMPT = current
        if hasattr(model_router, "SYSTEM_PROMPT"):
            model_router.SYSTEM_PROMPT = current


def _is_legacy_english_prompt(value: str) -> bool:
    """Prevents old bundled English defaults from overriding Chinese prompts."""

    legacy_markers = (
        "Output strict JSON only",
        "Generate runnable ManimCE code",
        "You are a senior teaching-animation director",
        "Repair this Manim Community Edition code",
    )
    return any(marker in value for marker in legacy_markers)
