from datetime import datetime
from uuid import uuid4

from backend.workflow.schemas import WorkflowEdge, WorkflowGraph, WorkflowNode, WorkflowPosition


def _node(node_id: str, node_type: str, x: int, y: int, **params) -> WorkflowNode:
    return WorkflowNode(id=node_id, type=node_type, position=WorkflowPosition(x=x, y=y), params=params)


def _edge(source: str, source_handle: str, target: str, target_handle: str) -> WorkflowEdge:
    return WorkflowEdge(id=f"e_{source}_{source_handle}_{target}_{target_handle}", source=source, sourceHandle=source_handle, target=target, targetHandle=target_handle)


def _base_workflow(name: str, description: str) -> WorkflowGraph:
    now = datetime.now().isoformat(timespec="seconds")
    return WorkflowGraph(
        workflow_id=f"wf_{uuid4().hex[:8]}",
        workflow_name=name,
        description=description,
        created_at=now,
        updated_at=now,
        template_info={"builtin": True, "name": name},
    )


def math_function_template() -> WorkflowGraph:
    workflow = _base_workflow("Math Function Explainer", "Prompt-driven teaching animation workflow.")
    workflow.nodes = [
        _node("prompt", "PromptInputNode", 80, 120, prompt="Explain vector projection with a simple diagram."),
        _node("model", "ModelConfigNode", 80, 300, provider="deepseek", base_url="https://api.deepseek.com/v1", model="deepseek-v4-pro"),
        _node("plan", "TeachingPlanNode", 360, 120),
        _node("storyboard", "StoryboardNode", 620, 120),
        _node("subtitles", "SubtitleNode", 880, 60),
        _node("code", "ManimCodeNode", 880, 210),
        _node("render", "RenderNode", 1140, 210, quality="low"),
        _node("output", "OutputNode", 1400, 160),
        _node("preview", "PreviewNode", 1660, 160),
    ]
    workflow.edges = [
        _edge("prompt", "prompt", "plan", "prompt"),
        _edge("model", "model_config", "plan", "model_config"),
        _edge("plan", "teaching_plan", "storyboard", "teaching_plan"),
        _edge("model", "model_config", "storyboard", "model_config"),
        _edge("storyboard", "storyboard", "subtitles", "storyboard"),
        _edge("storyboard", "storyboard", "code", "storyboard"),
        _edge("model", "model_config", "code", "model_config"),
        _edge("code", "manim_code", "render", "manim_code"),
        _edge("render", "video", "output", "video"),
        _edge("subtitles", "subtitles", "output", "subtitles"),
        _edge("code", "python_file", "output", "python_file"),
        _edge("render", "video", "preview", "video"),
    ]
    return workflow


def image_problem_template() -> WorkflowGraph:
    workflow = _base_workflow("Image Problem Explainer", "Image plus prompt workflow.")
    workflow.nodes = [
        _node("image", "InputImageNode", 80, 80),
        _node("prompt", "PromptInputNode", 80, 260, prompt="Explain the uploaded image as a teaching animation."),
        _node("model", "ModelConfigNode", 80, 440, provider="deepseek", base_url="https://api.deepseek.com/v1", model="deepseek-v4-pro"),
        _node("preprocess", "ImagePreprocessNode", 340, 80),
        _node("understand", "ImageUnderstandNode", 600, 80),
        _node("plan", "TeachingPlanNode", 860, 180),
        _node("storyboard", "StoryboardNode", 1120, 180),
        _node("subtitles", "SubtitleNode", 1380, 80),
        _node("code", "ManimCodeNode", 1380, 260),
        _node("render", "RenderNode", 1640, 260, quality="low"),
        _node("output", "OutputNode", 1900, 200),
        _node("preview", "PreviewNode", 2160, 200),
    ]
    workflow.edges = [
        _edge("image", "image", "preprocess", "image"),
        _edge("preprocess", "processed_image", "understand", "image"),
        _edge("model", "model_config", "understand", "model_config"),
        _edge("prompt", "prompt", "plan", "prompt"),
        _edge("understand", "image_understanding", "plan", "image_understanding"),
        _edge("model", "model_config", "plan", "model_config"),
        _edge("plan", "teaching_plan", "storyboard", "teaching_plan"),
        _edge("storyboard", "storyboard", "subtitles", "storyboard"),
        _edge("storyboard", "storyboard", "code", "storyboard"),
        _edge("model", "model_config", "code", "model_config"),
        _edge("code", "manim_code", "render", "manim_code"),
        _edge("render", "video", "output", "video"),
        _edge("subtitles", "subtitles", "output", "subtitles"),
        _edge("code", "python_file", "output", "python_file"),
        _edge("render", "video", "preview", "video"),
    ]
    return workflow


def mechanics_template() -> WorkflowGraph:
    workflow = math_function_template()
    workflow.workflow_id = f"wf_{uuid4().hex[:8]}"
    workflow.workflow_name = "Engineering Mechanics Beam"
    workflow.description = "Prompt-driven workflow for simple beam, support, load, reaction, and diagram explanation."
    for node in workflow.nodes:
        if node.id == "prompt":
            node.params["prompt"] = "Explain a simply supported beam with a central point load, reactions, shear, and bending moment intuition."
    workflow.template_info = {"builtin": True, "name": workflow.workflow_name}
    return workflow


TEMPLATES = {
    "math_function": math_function_template,
    "image_problem": image_problem_template,
    "mechanics_beam": mechanics_template,
}


def list_templates() -> list[dict[str, str]]:
    return [
        {"id": "math_function", "name": "Math Function Explainer"},
        {"id": "image_problem", "name": "Image Problem Explainer"},
        {"id": "mechanics_beam", "name": "Engineering Mechanics Beam"},
    ]


def get_template(template_id: str) -> WorkflowGraph | None:
    builder = TEMPLATES.get(template_id)
    return builder() if builder else None
