from pathlib import Path

from backend.ai import prompt_store
from backend.main import project_status, projects_root


def test_root_projects_lists_only_finished_videos(tmp_path: Path):
    finished = tmp_path / "finished_project"
    (finished / "outputs").mkdir(parents=True)
    (finished / "inputs").mkdir()
    (finished / "outputs" / "animation.mp4").write_bytes(b"video")
    (finished / "inputs" / "user_prompt.txt").write_text("介绍中国铁路", encoding="utf-8")

    unfinished = tmp_path / "unfinished_project"
    (unfinished / "segments" / "part_01").mkdir(parents=True)
    (unfinished / "segments" / "part_01" / "preview.mp4").write_bytes(b"preview")

    payload = projects_root(str(tmp_path))

    assert payload["root_dir"] == str(tmp_path.resolve())
    assert len(payload["projects"]) == 1
    assert payload["projects"][0]["title"] == "介绍中国铁路"
    assert payload["projects"][0]["project_dir"] == str(finished.resolve())

    all_projects = projects_root(str(tmp_path), include_unfinished=True)
    assert len(all_projects["projects"]) == 2
    assert {project["status"] for project in all_projects["projects"]} == {"已完成", "未完成"}


def test_legacy_english_prompt_override_is_ignored(tmp_path: Path, monkeypatch):
    override = tmp_path / "prompt_overrides.json"
    override.write_text(
        '{"prompts":{"SYSTEM_PROMPT":"You are a senior teaching-animation director. Output strict JSON only."}}',
        encoding="utf-8",
    )
    original = prompt_store.prompts.SYSTEM_PROMPT
    monkeypatch.setattr(prompt_store.prompts, "SYSTEM_PROMPT", "中文系统提示词")

    loaded = prompt_store.load_prompt_overrides(override)

    assert loaded == {}
    assert prompt_store.prompts.SYSTEM_PROMPT.startswith("中文系统提示词")
    assert "视觉与事实正确性硬性规则：" in prompt_store.prompts.SYSTEM_PROMPT
    monkeypatch.setattr(prompt_store.prompts, "SYSTEM_PROMPT", original)


def test_system_prompt_always_includes_general_visual_correctness_rules(tmp_path: Path, monkeypatch):
    override = tmp_path / "prompt_overrides.json"
    override.write_text(
        '{"prompts":{"SYSTEM_PROMPT":"自定义中文系统提示词"}}',
        encoding="utf-8",
    )
    original = prompt_store.prompts.SYSTEM_PROMPT
    monkeypatch.setattr(prompt_store.prompts, "SYSTEM_PROMPT", "默认中文系统提示词")

    prompt_store.load_prompt_overrides(override)

    active = prompt_store.get_prompt_values()["SYSTEM_PROMPT"]
    assert active.startswith("自定义中文系统提示词")
    assert "视觉与事实正确性硬性规则：" in active
    assert "共享同一份几何或数据来源" in active
    monkeypatch.setattr(prompt_store.prompts, "SYSTEM_PROMPT", original)


def test_project_status_loads_output_video_without_stitched_copy(tmp_path: Path):
    project = tmp_path / "project"
    (project / "outputs").mkdir(parents=True)
    output = project / "outputs" / "animation.mp4"
    output.write_bytes(b"video")

    payload = project_status(str(project))

    assert payload["summary"]["video_path"] == str(output.resolve())
