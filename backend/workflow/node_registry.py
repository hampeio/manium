import json
import re
from pathlib import Path

from pydantic import ValidationError

from backend.workflow.schemas import NodeDefinition, PortDefinition


def _port(name: str, type_: str, required: bool = False, description: str = "", default=None) -> PortDefinition:
    return PortDefinition(name=name, type=type_, required=required, description=description, default=default)


NODE_DEFINITIONS: dict[str, NodeDefinition] = {
    "InputImageNode": NodeDefinition(
        type="InputImageNode",
        label="Input Image",
        category="input",
        description="Image input node.",
        outputs=[_port("image", "Image", description="Uploaded image path.")],
    ),
    "PromptInputNode": NodeDefinition(
        type="PromptInputNode",
        label="Prompt",
        category="input",
        description="Prompt text input.",
        outputs=[_port("prompt", "Prompt", required=True, description="User teaching prompt.")],
        default_params={"prompt": "Explain vector projection with a simple diagram."},
    ),
    "ModelConfigNode": NodeDefinition(
        type="ModelConfigNode",
        label="Model Config",
        category="input",
        description="Provider, base URL, and model name. API keys are never saved in workflow JSON.",
        outputs=[_port("model_config", "ModelConfig", description="Resolved model configuration.")],
        default_params={"provider": "deepseek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-v4-pro"},
    ),
    "ImagePreprocessNode": NodeDefinition(
        type="ImagePreprocessNode",
        label="Image Preprocess",
        category="image",
        description="Placeholder for format checks, copy, compression, OCR hooks, and annotation hooks.",
        inputs=[_port("image", "Image", required=True)],
        outputs=[_port("processed_image", "Image")],
    ),
    "ImageUnderstandNode": NodeDefinition(
        type="ImageUnderstandNode",
        label="Image Understand",
        category="ai",
        description="Image understanding node.",
        inputs=[_port("image", "Image", required=True), _port("model_config", "ModelConfig")],
        outputs=[_port("image_understanding", "Text")],
    ),
    "TeachingPlanNode": NodeDefinition(
        type="TeachingPlanNode",
        label="Teaching Plan",
        category="planning",
        description="Generates teaching goals.",
        inputs=[_port("prompt", "Prompt"), _port("image_understanding", "Text"), _port("model_config", "ModelConfig")],
        outputs=[_port("teaching_plan", "Markdown")],
    ),
    "StoryboardNode": NodeDefinition(
        type="StoryboardNode",
        label="Storyboard",
        category="planning",
        description="Generates 3-5 storyboard scenes.",
        inputs=[_port("teaching_plan", "Markdown", required=True), _port("model_config", "ModelConfig")],
        outputs=[_port("storyboard", "StoryboardJSON")],
    ),
    "SubtitleNode": NodeDefinition(
        type="SubtitleNode",
        label="Subtitles",
        category="planning",
        description="Generates SRT and JSON timeline subtitles.",
        inputs=[_port("storyboard", "StoryboardJSON", required=True)],
        outputs=[_port("subtitles", "SubtitleJSON")],
    ),
    "ManimCodeNode": NodeDefinition(
        type="ManimCodeNode",
        label="Manim Code",
        category="code",
        description="Generates Manim Community Edition Python code.",
        inputs=[_port("storyboard", "StoryboardJSON", required=True), _port("model_config", "ModelConfig")],
        outputs=[_port("manim_code", "ManimCode"), _port("python_file", "PythonFile")],
    ),
    "RenderNode": NodeDefinition(
        type="RenderNode",
        label="Render",
        category="render",
        description="Runs Manim and owns the internal repair loop.",
        inputs=[_port("manim_code", "ManimCode", required=True)],
        outputs=[_port("video", "VideoFile"), _port("render_log", "Log"), _port("error", "ErrorReport")],
        default_params={"quality": "low"},
    ),
    "RepairNode": NodeDefinition(
        type="RepairNode",
        label="Repair",
        category="render",
        description="Visible repair marker. Actual repair loop is encapsulated by RenderNode.",
        inputs=[_port("error", "ErrorReport")],
        outputs=[_port("repair_log", "Log")],
    ),
    "OutputNode": NodeDefinition(
        type="OutputNode",
        label="Output",
        category="output",
        description="Collects output artifacts.",
        inputs=[_port("video", "VideoFile"), _port("subtitles", "SubtitleJSON"), _port("python_file", "PythonFile")],
        outputs=[_port("project_path", "ProjectPath")],
    ),
    "PreviewNode": NodeDefinition(
        type="PreviewNode",
        label="Preview",
        category="output",
        description="Loads video result into the desktop preview player.",
        inputs=[_port("video", "VideoFile", required=True)],
        outputs=[_port("preview", "Any")],
    ),
    "CommentNode": NodeDefinition(
        type="CommentNode",
        label="Comment",
        category="comment",
        description="Canvas-only note. Not executed.",
        default_params={"text": "Note"},
    ),
    "VideoInputNode": NodeDefinition(
        type="VideoInputNode", label="视频上传", category="input",
        description="上传参考视频并输出本地视频路径。",
        outputs=[_port("video", "VideoFile", description="上传的视频文件。")],
        default_params={"file_path": ""},
    ),
    "StyleReferenceNode": NodeDefinition(
        type="StyleReferenceNode", label="风格参考", category="reference",
        description="提供色彩、构图、节奏和动画风格参考。",
        inputs=[_port("image", "Image"), _port("video", "VideoFile"), _port("text", "Text")],
        outputs=[_port("style_reference", "Text")],
        default_params={"style_prompt": "深色背景、清晰层级、连续动画"},
    ),
    "CharacterReferenceNode": NodeDefinition(
        type="CharacterReferenceNode", label="角色参考", category="reference",
        description="定义角色外观、名称和一致性要求。",
        inputs=[_port("image", "Image")], outputs=[_port("character_reference", "Text")],
        default_params={"character_name": "", "description": ""},
    ),
    "SceneReferenceNode": NodeDefinition(
        type="SceneReferenceNode", label="场景参考", category="reference",
        description="描述场景环境、空间布局与关键物体。",
        inputs=[_port("image", "Image")], outputs=[_port("scene_reference", "Text")],
        default_params={"description": ""},
    ),
    "CameraMotionNode": NodeDefinition(
        type="CameraMotionNode", label="镜头运动", category="control",
        description="设置推拉、平移、缩放或固定镜头。",
        inputs=[_port("storyboard", "StoryboardJSON")], outputs=[_port("camera_plan", "Text")],
        default_params={"motion": "static", "strength": 0.5},
    ),
    "DurationControlNode": NodeDefinition(
        type="DurationControlNode", label="时长控制", category="control",
        description="设置总时长、片段时长和节奏。",
        inputs=[_port("prompt", "Prompt")], outputs=[_port("duration_config", "Any")],
        default_params={"total_seconds": 300, "compact_timing": True},
    ),
    "ResolutionNode": NodeDefinition(
        type="ResolutionNode", label="分辨率设置", category="control",
        description="设置预览或正式渲染分辨率。",
        outputs=[_port("render_config", "Any")],
        default_params={"quality": "preview_720p", "width": 1280, "height": 720},
    ),
    "ConditionNode": NodeDefinition(
        type="ConditionNode", label="条件判断", category="logic",
        description="根据参数表达式选择真或假分支。",
        inputs=[_port("value", "Any", required=True)], outputs=[_port("true", "Any"), _port("false", "Any")],
        default_params={"operator": "exists", "expected": ""},
    ),
    "BranchNode": NodeDefinition(
        type="BranchNode", label="多分支", category="logic",
        description="将一个上游结果复制到多个可独立执行的分支。",
        inputs=[_port("input", "Any", required=True)],
        outputs=[_port("branch_a", "Any"), _port("branch_b", "Any"), _port("branch_c", "Any")],
    ),
    "MergeNode": NodeDefinition(
        type="MergeNode", label="合并", category="logic",
        description="等待多个分支完成后合并输出。",
        inputs=[_port("input_a", "Any"), _port("input_b", "Any"), _port("input_c", "Any")],
        outputs=[_port("merged", "Any")],
        default_params={"strategy": "all"},
    ),
}

BUILTIN_NODE_TYPES = set(NODE_DEFINITIONS)
CUSTOM_NODE_DIR = Path("custom_nodes")


def register_custom_node(payload: dict, *, persist: bool = True) -> NodeDefinition:
    missing = [field for field in ("type", "label", "category", "description", "inputs", "outputs") if field not in payload]
    if missing:
        raise ValueError("节点配置缺少字段：" + "、".join(missing))
    node_type = str(payload.get("type", ""))
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*Node", node_type):
        raise ValueError("type 必须是英文标识并以 Node 结尾，例如 MyCustomNode。")
    if node_type in BUILTIN_NODE_TYPES:
        raise ValueError(f"不能覆盖内置节点：{node_type}")
    try:
        definition = NodeDefinition.model_validate(payload)
    except ValidationError as exc:
        errors = "；".join(".".join(str(item) for item in error["loc"]) + "：" + error["msg"] for error in exc.errors())
        raise ValueError("节点配置格式错误：" + errors) from exc
    NODE_DEFINITIONS[node_type] = definition
    if persist:
        CUSTOM_NODE_DIR.mkdir(parents=True, exist_ok=True)
        (CUSTOM_NODE_DIR / f"{node_type}.json").write_text(
            definition.model_dump_json(indent=2), encoding="utf-8"
        )
    return definition


def _load_custom_nodes() -> None:
    if not CUSTOM_NODE_DIR.exists():
        return
    for path in CUSTOM_NODE_DIR.glob("*.json"):
        try:
            register_custom_node(json.loads(path.read_text(encoding="utf-8")), persist=False)
        except (OSError, ValueError, json.JSONDecodeError):
            continue


def list_node_definitions() -> list[NodeDefinition]:
    return list(NODE_DEFINITIONS.values())


def get_node_definition(node_type: str) -> NodeDefinition | None:
    return NODE_DEFINITIONS.get(node_type)


_load_custom_nodes()
