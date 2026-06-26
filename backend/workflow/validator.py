from collections import defaultdict, deque

from backend.workflow.node_registry import get_node_definition
from backend.workflow.schemas import ValidationIssue, WorkflowGraph, WorkflowValidationResult


def validate_workflow(workflow: WorkflowGraph) -> WorkflowValidationResult:
    issues: list[ValidationIssue] = []
    node_ids = [node.id for node in workflow.nodes]
    node_id_set = set(node_ids)

    if len(node_ids) != len(node_id_set):
        issues.append(ValidationIssue(severity="error", message="Duplicate node id found."))

    node_by_id = {node.id: node for node in workflow.nodes}
    for node in workflow.nodes:
        definition = get_node_definition(node.type)
        if not definition:
            issues.append(ValidationIssue(severity="error", node_id=node.id, message=f"Unknown node type: {node.type}"))

    if not any(node.type in {"PromptInputNode", "InputImageNode"} for node in workflow.nodes):
        issues.append(ValidationIssue(severity="error", message="Workflow needs at least one prompt or image input node."))
    if not any(node.type == "OutputNode" for node in workflow.nodes):
        issues.append(ValidationIssue(severity="error", message="Workflow needs an OutputNode."))

    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    connected_targets = {(edge.target, edge.targetHandle) for edge in workflow.edges}

    for edge in workflow.edges:
        if edge.source not in node_id_set:
            issues.append(ValidationIssue(severity="error", edge_id=edge.id, message=f"Invalid source node: {edge.source}"))
            continue
        if edge.target not in node_id_set:
            issues.append(ValidationIssue(severity="error", edge_id=edge.id, message=f"Invalid target node: {edge.target}"))
            continue
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)
        _validate_edge_ports(workflow, edge.id, node_by_id[edge.source], node_by_id[edge.target], edge.sourceHandle, edge.targetHandle, issues)

    for node in workflow.nodes:
        definition = get_node_definition(node.type)
        if not definition:
            continue
        for port in definition.inputs:
            if port.required and (node.id, port.name) not in connected_targets and port.default is None:
                issues.append(ValidationIssue(severity="error", node_id=node.id, message=f"Required input not connected: {port.name}"))

    order, cycle_found = _topological_order(node_ids, outgoing, incoming)
    if cycle_found:
        issues.append(ValidationIssue(severity="error", message="Workflow must be a DAG; cycle detected."))

    return WorkflowValidationResult(valid=not any(issue.severity == "error" for issue in issues), issues=issues, execution_order=order)


def _validate_edge_ports(workflow: WorkflowGraph, edge_id: str, source_node, target_node, source_handle: str, target_handle: str, issues: list[ValidationIssue]) -> None:
    source_def = get_node_definition(source_node.type)
    target_def = get_node_definition(target_node.type)
    if not source_def or not target_def:
        return
    source_port = next((port for port in source_def.outputs if port.name == source_handle), None)
    target_port = next((port for port in target_def.inputs if port.name == target_handle), None)
    if not source_port:
        issues.append(ValidationIssue(severity="error", edge_id=edge_id, message=f"Unknown source port: {source_handle}"))
        return
    if not target_port:
        issues.append(ValidationIssue(severity="error", edge_id=edge_id, message=f"Unknown target port: {target_handle}"))
        return
    if source_port.type != target_port.type and source_port.type != "Any" and target_port.type != "Any":
        issues.append(
            ValidationIssue(
                severity="error",
                edge_id=edge_id,
                message=f"Incompatible ports: {source_port.type} -> {target_port.type}",
            )
        )


def _topological_order(node_ids: list[str], outgoing: dict[str, list[str]], incoming: dict[str, list[str]]) -> tuple[list[str], bool]:
    indegree = {node_id: len(incoming[node_id]) for node_id in node_ids}
    queue = deque([node_id for node_id in node_ids if indegree[node_id] == 0])
    order: list[str] = []
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return order, len(order) != len(node_ids)
