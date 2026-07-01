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
}


def list_node_definitions() -> list[NodeDefinition]:
    return list(NODE_DEFINITIONS.values())


def get_node_definition(node_type: str) -> NodeDefinition | None:
    return NODE_DEFINITIONS.get(node_type)
