import json
from pathlib import Path
from uuid import uuid4

from backend.services.generation_service import GenerationService
from backend.services.project_manager import ProjectManager
from backend.workflow.schemas import WorkflowGraph
from backend.workflow.validator import validate_workflow


class WorkflowExecutor:
    """First-pass workflow executor that validates a DAG and delegates to the fixed generation pipeline."""

    def __init__(self, generation_service: GenerationService, project_manager: ProjectManager):
        self.generation_service = generation_service
        self.project_manager = project_manager

    async def run(self, workflow: WorkflowGraph, project_dir: Path, model_router, quality: str, progress=None) -> dict[str, object]:
        emit = progress or (lambda _message: None)
        validation = validate_workflow(workflow)
        workflow_dir = project_dir / "workflow"
        workflow_dir.mkdir(parents=True, exist_ok=True)
        (workflow_dir / "workflow.json").write_text(workflow.model_dump_json(indent=2), encoding="utf-8")
        (workflow_dir / "validation.json").write_text(validation.model_dump_json(indent=2), encoding="utf-8")
        if not validation.valid:
            raise ValueError("工作流验证失败：" + "；".join(issue.message for issue in validation.issues))

        emit("工作流有向无环图验证通过。")
        for node_id in validation.execution_order:
            node = next(node for node in workflow.nodes if node.id == node_id)
            node_dir = project_dir / "workflow_outputs" / node.id
            node_dir.mkdir(parents=True, exist_ok=True)
            (node_dir / "input_snapshot.json").write_text(json.dumps(node.params, ensure_ascii=False, indent=2), encoding="utf-8")
            (node_dir / "node.log").write_text(f"Node {node.id} ({node.type}) scheduled in first-pass executor.\n", encoding="utf-8")
            (node_dir / "output.json").write_text(json.dumps({"status": "scheduled", "node_type": node.type}, ensure_ascii=False, indent=2), encoding="utf-8")

        prompt = _first_param(workflow, "PromptInputNode", "prompt") or "Explain vector projection with a simple diagram."
        emit("正在将工作流交给生成管线执行。")
        result = await self.generation_service.run(
            project_dir=project_dir,
            user_prompt=prompt,
            uploaded_image=None,
            model_router=model_router,
            quality=quality,
            project_manager=self.project_manager,
            progress=progress,
        )
        result["workflow_id"] = workflow.workflow_id or f"wf_{uuid4().hex[:8]}"
        result["workflow_outputs_dir"] = str((project_dir / "workflow_outputs").resolve())
        return result


def _first_param(workflow: WorkflowGraph, node_type: str, param_name: str):
    for node in workflow.nodes:
        if node.type == node_type and param_name in node.params:
            return node.params[param_name]
    return None
