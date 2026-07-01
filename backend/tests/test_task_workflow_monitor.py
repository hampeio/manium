import sys
from datetime import datetime, timedelta

import pytest

from backend.rendering.manim_renderer import ManimRenderer
from backend.services.task_registry import TaskRegistry
from backend.workflow.node_registry import get_node_definition, register_custom_node


def test_task_registry_persists_progress_and_marks_interrupted(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    registry = TaskRegistry(tmp_path)
    task = registry.create(str(project))
    registry.start(task.task_id)
    registry.log(task.task_id, "片段 3/10：正在渲染。")

    payload = registry.to_dict(task.task_id)
    assert payload["state"] == "running"
    assert payload["current_stage"] == "rendering"
    assert payload["progress_percent"] >= 70
    assert (project / "task_status.json").exists()

    reloaded = TaskRegistry(tmp_path)
    interrupted = reloaded.to_dict(task.task_id)
    assert interrupted["state"] == "interrupted"
    assert "后台服务曾重启" in interrupted["error"]


def test_task_registry_detects_missing_heartbeat(tmp_path):
    registry = TaskRegistry(tmp_path, stall_timeout_seconds=1)
    task = registry.create()
    registry.start(task.task_id)
    task.heartbeat_at = (datetime.now() - timedelta(seconds=5)).isoformat(timespec="seconds")

    payload = registry.to_dict(task.task_id)

    assert payload["state"] == "stalled"
    assert "没有心跳" in payload["error"]


def test_requested_workflow_nodes_and_custom_node_validation():
    for node_type in [
        "VideoInputNode",
        "StyleReferenceNode",
        "CharacterReferenceNode",
        "SceneReferenceNode",
        "CameraMotionNode",
        "DurationControlNode",
        "ResolutionNode",
        "ConditionNode",
        "BranchNode",
        "MergeNode",
    ]:
        assert get_node_definition(node_type) is not None

    with pytest.raises(ValueError, match="缺少字段"):
        register_custom_node({"type": "BrokenNode"}, persist=False)

    definition = register_custom_node(
        {
            "type": "UnitTestCustomNode",
            "label": "测试节点",
            "category": "custom",
            "description": "测试自定义节点。",
            "inputs": [{"name": "input", "type": "Any"}],
            "outputs": [{"name": "output", "type": "Any"}],
        },
        persist=False,
    )
    assert definition.label == "测试节点"


@pytest.mark.anyio
async def test_manim_renderer_terminates_a_timed_out_process(tmp_path):
    sleeper = tmp_path / "sleeper.py"
    sleeper.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    renderer = ManimRenderer(f"{sys.executable} {sleeper}", timeout_seconds=1)
    scene = tmp_path / "scene.py"
    scene.write_text("from manim import *\n", encoding="utf-8")

    result = await renderer.render(scene, "GeneratedTeachingScene", tmp_path / "media", "low")

    assert not result.success
    assert result.timed_out
    assert "渲染超时" in result.stderr
