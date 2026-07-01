import json
from pathlib import Path
from uuid import uuid4

from backend.services.generation_service import GenerationService
from backend.services.project_manager import ProjectManager
from backend.workflow.node_registry import get_node_definition
from backend.workflow.schemas import WorkflowGraph
from backend.workflow.validator import validate_workflow


class WorkflowExecutor:
    """Executes a validated DAG, persists node states, and delegates media generation."""

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

        states = {
            node.id: {"node_id": node.id, "type": node.type, "status": "idle", "error": None, "inputs": {}, "outputs": {}}
            for node in workflow.nodes
        }
        self._write_states(workflow_dir, states)
        values: dict[tuple[str, str], object] = {}
        incoming = {}
        for edge in workflow.edges:
            incoming.setdefault(edge.target, []).append(edge)

        emit("执行节点工作流中：拓扑顺序验证通过。")
        for node_id in validation.execution_order:
            node = next(node for node in workflow.nodes if node.id == node_id)
            definition = get_node_definition(node.type)
            node_inputs = {
                edge.targetHandle: values.get((edge.source, edge.sourceHandle))
                for edge in incoming.get(node.id, [])
            }
            states[node.id].update(status="running", inputs=node_inputs)
            self._write_states(workflow_dir, states)
            emit(f"节点 {node.label or definition.label if definition else node.id}：运行中。")
            try:
                outputs = self._execute_configuration_node(node.type, node.params, node_inputs, definition)
                for name, value in outputs.items():
                    values[(node.id, name)] = value
                states[node.id].update(status="success", outputs=outputs)
                self._write_node_output(project_dir, node.id, node.type, node.params, node_inputs, outputs)
                emit(f"节点 {node.label or definition.label if definition else node.id}：已完成。")
            except Exception as exc:
                states[node.id].update(status="failed", error=str(exc))
                self._write_states(workflow_dir, states)
                raise RuntimeError(f"节点 {node.id}（{node.type}）执行失败：{exc}") from exc

        prompt = _first_param(workflow, "PromptInputNode", "prompt") or "Explain vector projection with a simple diagram."
        image_value = _first_param(workflow, "InputImageNode", "file_path")
        uploaded_image = Path(str(image_value)).resolve() if image_value else None
        if uploaded_image and not uploaded_image.exists():
            raise FileNotFoundError(f"图片输入节点文件不存在：{uploaded_image}")
        duration = int(_first_param(workflow, "DurationControlNode", "total_seconds") or 300)
        render_quality = _first_param(workflow, "ResolutionNode", "quality") or quality
        emit("生成视频中：节点参数已汇总，正在执行生成管线。")
        try:
            result = await self.generation_service.run(
                project_dir=project_dir,
                user_prompt=prompt,
                uploaded_image=uploaded_image,
                model_router=model_router,
                quality=render_quality,
                total_duration_seconds=duration,
                project_manager=self.project_manager,
                progress=progress,
            )
        except Exception as exc:
            render_nodes = [node for node in workflow.nodes if node.type in {"RenderNode", "OutputNode"}]
            failed_node = render_nodes[0] if render_nodes else workflow.nodes[-1]
            states[failed_node.id].update(status="failed", error=str(exc))
            self._write_states(workflow_dir, states)
            raise RuntimeError(f"节点 {failed_node.id} 执行失败：{exc}") from exc

        result["workflow_id"] = workflow.workflow_id or f"wf_{uuid4().hex[:8]}"
        result["workflow_outputs_dir"] = str((project_dir / "workflow_outputs").resolve())
        result["workflow_node_states"] = states
        return result

    def _execute_configuration_node(self, node_type, params, inputs, definition):
        if node_type == "PromptInputNode":
            return {"prompt": params.get("prompt", "")}
        if node_type == "InputImageNode":
            return {"image": params.get("file_path", "")}
        if node_type == "VideoInputNode":
            return {"video": params.get("file_path", "")}
        if node_type == "ModelConfigNode":
            return {"model_config": params}
        if node_type == "ConditionNode":
            value = inputs.get("value")
            matched = bool(value) if params.get("operator") == "exists" else str(value) == str(params.get("expected"))
            return {"true": value if matched else None, "false": None if matched else value}
        if node_type == "BranchNode":
            value = inputs.get("input")
            return {"branch_a": value, "branch_b": value, "branch_c": value}
        if node_type == "MergeNode":
            return {"merged": [value for value in inputs.values() if value is not None]}
        return {port.name: {"params": params, "inputs": inputs} for port in (definition.outputs if definition else [])}

    def _write_node_output(self, project_dir, node_id, node_type, params, inputs, outputs):
        node_dir = project_dir / "workflow_outputs" / node_id
        node_dir.mkdir(parents=True, exist_ok=True)
        (node_dir / "input_snapshot.json").write_text(
            json.dumps({"params": params, "upstream": inputs}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (node_dir / "output.json").write_text(
            json.dumps({"status": "success", "node_type": node_type, "outputs": outputs}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_states(self, workflow_dir, states):
        (workflow_dir / "node_states.json").write_text(
            json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _first_param(workflow: WorkflowGraph, node_type: str, param_name: str):
    for node in workflow.nodes:
        if node.type == node_type and param_name in node.params:
            return node.params[param_name]
    return None
