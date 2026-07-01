from typing import Any, Literal

from pydantic import BaseModel, Field


PortType = Literal[
    "Image",
    "Text",
    "Prompt",
    "ModelConfig",
    "Markdown",
    "StoryboardJSON",
    "SubtitleJSON",
    "ManimCode",
    "PythonFile",
    "VideoFile",
    "AudioFile",
    "Log",
    "ProjectPath",
    "ErrorReport",
    "Any",
]

NodeStatus = Literal["idle", "waiting_input", "queued", "running", "success", "failed", "skipped", "stopped"]


class PortDefinition(BaseModel):
    name: str
    type: PortType
    required: bool = False
    default: Any = None
    description: str = ""


class NodeDefinition(BaseModel):
    type: str
    label: str
    category: str
    description: str
    inputs: list[PortDefinition] = Field(default_factory=list)
    outputs: list[PortDefinition] = Field(default_factory=list)
    default_params: dict[str, Any] = Field(default_factory=dict)


class WorkflowPosition(BaseModel):
    x: float
    y: float


class WorkflowNode(BaseModel):
    id: str
    type: str
    label: str | None = None
    position: WorkflowPosition = Field(default_factory=lambda: WorkflowPosition(x=0, y=0))
    params: dict[str, Any] = Field(default_factory=dict)
    status: NodeStatus = "idle"


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: str
    targetHandle: str


class WorkflowViewport(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = 1


class WorkflowGraph(BaseModel):
    workflow_id: str = "workflow"
    workflow_name: str = "Untitled Workflow"
    workflow_version: str = "1.0"
    app_version: str = "0.1.0"
    description: str = ""
    created_at: str | None = None
    updated_at: str | None = None
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    viewport: WorkflowViewport = Field(default_factory=WorkflowViewport)
    template_info: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    message: str
    node_id: str | None = None
    edge_id: str | None = None


class WorkflowValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue]
    execution_order: list[str] = Field(default_factory=list)
