import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.ai.model_config import resolve_model_config
from backend.ai.model_router import ModelRouter
from backend.ai.prompt_store import apply_prompt_overrides, get_prompt_values, load_prompt_overrides
from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.services.generation_service import GenerationService
from backend.services.project_manager import ProjectManager
from backend.services.task_registry import TaskRegistry
from backend.workflow.executor import WorkflowExecutor
from backend.workflow.node_registry import list_node_definitions
from backend.workflow.schemas import WorkflowGraph
from backend.workflow.templates import get_template, list_templates
from backend.workflow.validator import validate_workflow

settings = get_settings()
load_prompt_overrides()
configure_logging(
    [
        settings.openai_api_key,
        settings.deepseek_api_key,
        settings.xunfei_api_key,
        settings.xunfei_api_secret,
        settings.fish_tts_api_key,
    ]
)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "file://", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project_manager = ProjectManager(settings.generated_projects_dir)
generation_service = GenerationService(settings, project_manager)
task_registry = TaskRegistry()
workflow_executor = WorkflowExecutor(generation_service, project_manager)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/prompts")
def prompts_get() -> dict[str, object]:
    return {"prompts": get_prompt_values()}


@app.post("/prompts")
async def prompts_post(payload: dict[str, object]) -> dict[str, object]:
    values = payload.get("prompts", payload)
    if not isinstance(values, dict):
        raise HTTPException(status_code=400, detail="Invalid prompt payload")
    return {"prompts": apply_prompt_overrides(values)}


@app.post("/generate")
async def generate(
    prompt: str = Form(default=""),
    provider: str = Form(default=""),
    api_key: str = Form(default=""),
    base_url: str = Form(default=""),
    model: str = Form(default=""),
    quality: str = Form(default="preview_720p"),
    total_duration_seconds: int = Form(default=300),
    storyboard_scene_count: int = Form(default=0),
    compact_timing: bool = Form(default=False),
    output_dir: str = Form(default=""),
    image: UploadFile | None = File(default=None),
) -> dict[str, object]:
    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    image_path = await active_manager.save_upload(project_dir, image)
    model_config = resolve_model_config(settings, provider or None, api_key or None, base_url or None, model or None)
    try:
        return await generation_service.run(
            project_dir=project_dir,
            user_prompt=prompt,
            uploaded_image=image_path,
            model_router=ModelRouter(model_config, trace_dir=project_dir / "ai_traces"),
            project_manager=active_manager,
            quality=quality,
            total_duration_seconds=total_duration_seconds,
            preferred_scene_count=storyboard_scene_count,
            compact_timing=compact_timing,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate_async")
async def generate_async(
    prompt: str = Form(default=""),
    provider: str = Form(default=""),
    api_key: str = Form(default=""),
    base_url: str = Form(default=""),
    model: str = Form(default=""),
    quality: str = Form(default="preview_720p"),
    total_duration_seconds: int = Form(default=300),
    storyboard_scene_count: int = Form(default=0),
    compact_timing: bool = Form(default=False),
    output_dir: str = Form(default=""),
    image: UploadFile | None = File(default=None),
) -> dict[str, object]:
    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    image_path = await active_manager.save_upload(project_dir, image)
    model_config = resolve_model_config(settings, provider or None, api_key or None, base_url or None, model or None)
    task = task_registry.create(str(project_dir.resolve()))

    async def run_job() -> None:
        task_registry.start(task.task_id)
        try:
            result = await generation_service.run(
                project_dir=project_dir,
                user_prompt=prompt,
                uploaded_image=image_path,
                model_router=ModelRouter(model_config, trace_dir=project_dir / "ai_traces"),
                project_manager=active_manager,
                quality=quality,
                total_duration_seconds=total_duration_seconds,
                preferred_scene_count=storyboard_scene_count,
                compact_timing=compact_timing,
                progress=lambda message: task_registry.log(task.task_id, message),
                pause_checker=lambda: task_registry.is_pause_requested(task.task_id),
                partial_update=lambda partial: task_registry.update_partial(task.task_id, partial),
            )
            task_registry.complete(task.task_id, result)
        except Exception as exc:
            task_registry.fail(task.task_id, str(exc))

    asyncio.create_task(run_job())
    return {"task_id": task.task_id, "project_dir": str(project_dir.resolve()), "state": "queued"}


@app.post("/regenerate_async")
async def regenerate_async(
    source_project_dir: str = Form(default=""),
    edit_prompt: str = Form(default=""),
    provider: str = Form(default=""),
    api_key: str = Form(default=""),
    base_url: str = Form(default=""),
    model: str = Form(default=""),
    quality: str = Form(default="preview_720p"),
    total_duration_seconds: int = Form(default=300),
    storyboard_scene_count: int = Form(default=0),
    compact_timing: bool = Form(default=True),
    output_dir: str = Form(default=""),
) -> dict[str, object]:
    source_dir = Path(source_project_dir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="Source project not found")
    original_prompt_path = source_dir / "inputs" / "user_prompt.txt"
    original_prompt = original_prompt_path.read_text(encoding="utf-8", errors="replace") if original_prompt_path.exists() else ""
    combined_prompt = (
        f"{original_prompt}\n\n"
        "请基于上一版结果应用以下修改要求，保持主题一致并重新生成视频：\n"
        f"{edit_prompt.strip() or '使用当前设置重新生成。'}"
    ).strip()

    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    active_manager.write_text(project_dir, "inputs/source_project_dir.txt", str(source_dir))
    active_manager.write_text(project_dir, "inputs/edit_prompt.txt", edit_prompt or "")
    model_config = resolve_model_config(settings, provider or None, api_key or None, base_url or None, model or None)
    task = task_registry.create(str(project_dir.resolve()))

    async def run_job() -> None:
        task_registry.start(task.task_id)
        try:
            result = await generation_service.run(
                project_dir=project_dir,
                user_prompt=combined_prompt,
                uploaded_image=None,
                model_router=ModelRouter(model_config, trace_dir=project_dir / "ai_traces"),
                project_manager=active_manager,
                quality=quality,
                total_duration_seconds=total_duration_seconds,
                preferred_scene_count=storyboard_scene_count,
                compact_timing=compact_timing,
                progress=lambda message: task_registry.log(task.task_id, message),
                pause_checker=lambda: task_registry.is_pause_requested(task.task_id),
                partial_update=lambda partial: task_registry.update_partial(task.task_id, partial),
            )
            task_registry.complete(task.task_id, result)
        except Exception as exc:
            task_registry.fail(task.task_id, str(exc))

    asyncio.create_task(run_job())
    return {"task_id": task.task_id, "project_dir": str(project_dir.resolve()), "state": "queued"}


@app.post("/replace_segment_async")
async def replace_segment_async(
    source_project_dir: str = Form(default=""),
    segment_id: str = Form(default=""),
    edit_prompt: str = Form(default=""),
    provider: str = Form(default=""),
    api_key: str = Form(default=""),
    base_url: str = Form(default=""),
    model: str = Form(default=""),
    quality: str = Form(default="preview_720p"),
) -> dict[str, object]:
    source_dir = Path(source_project_dir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="Source project not found")
    if not segment_id:
        raise HTTPException(status_code=400, detail="segment_id is required")
    model_config = resolve_model_config(settings, provider or None, api_key or None, base_url or None, model or None)
    task = task_registry.create(str(source_dir))

    async def run_job() -> None:
        task_registry.start(task.task_id)
        try:
            result = await generation_service.replace_segment(
                project_dir=source_dir,
                segment_id=segment_id,
                edit_prompt=edit_prompt,
                model_router=ModelRouter(model_config, trace_dir=source_dir / "ai_traces"),
                quality=quality,
                progress=lambda message: task_registry.log(task.task_id, message),
                partial_update=lambda partial: task_registry.update_partial(task.task_id, partial),
            )
            task_registry.complete(task.task_id, result)
        except Exception as exc:
            task_registry.fail(task.task_id, str(exc))

    asyncio.create_task(run_job())
    return {"task_id": task.task_id, "project_dir": str(source_dir), "state": "queued"}


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    task = task_registry.to_dict(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks/{task_id}/pause")
def pause_task(task_id: str) -> dict[str, object]:
    if not task_registry.pause(task_id):
        raise HTTPException(status_code=404, detail="Task not found or cannot be paused")
    return {"task_id": task_id, "state": "paused"}


@app.post("/tasks/{task_id}/resume")
def resume_task(task_id: str) -> dict[str, object]:
    if not task_registry.resume(task_id):
        raise HTTPException(status_code=404, detail="Task not found or cannot be resumed")
    return {"task_id": task_id, "state": "running"}


@app.get("/workflow/node-definitions")
def workflow_node_definitions() -> dict[str, object]:
    return {"nodes": [definition.model_dump() for definition in list_node_definitions()]}


@app.get("/workflow/templates")
def workflow_templates() -> dict[str, object]:
    return {"templates": list_templates()}


@app.get("/workflow/templates/{template_id}")
def workflow_template(template_id: str) -> dict[str, object]:
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.model_dump()


@app.post("/workflow/validate")
async def workflow_validate(workflow: WorkflowGraph) -> dict[str, object]:
    return validate_workflow(workflow).model_dump()


@app.post("/workflow/run_async")
async def workflow_run_async(
    workflow: WorkflowGraph,
    provider: str = "",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    quality: str = "low",
    output_dir: str = "",
) -> dict[str, object]:
    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    model_config = resolve_model_config(settings, provider or None, api_key or None, base_url or None, model or None)
    task = task_registry.create()

    async def run_job() -> None:
        task_registry.start(task.task_id)
        try:
            result = await workflow_executor.run(
                workflow=workflow,
                project_dir=project_dir,
                model_router=ModelRouter(model_config, trace_dir=project_dir / "ai_traces"),
                quality=quality,
                progress=lambda message: task_registry.log(task.task_id, message),
            )
            task_registry.complete(task.task_id, result)
        except Exception as exc:
            task_registry.fail(task.task_id, str(exc))

    asyncio.create_task(run_job())
    return {"task_id": task.task_id, "project_dir": str(project_dir.resolve()), "state": "queued"}


@app.get("/video")
def video(path: str) -> FileResponse:
    video_path = Path(path)
    if not video_path.exists() or video_path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video_path, media_type="video/mp4")


@app.head("/video")
def video_head(path: str) -> FileResponse:
    return video(path)


@app.get("/project/status")
def project_status(project_dir: str) -> dict[str, object]:
    root = Path(project_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")

    def read_json(name: str, default: object) -> object:
        path = root / name
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))

    stage_manifest = read_json("stage_manifest.json", {})
    segment_manifest = read_json("segment_manifest.json", {})
    final_summary = read_json("final_summary.json", {})
    segments = segment_manifest.get("segments", []) if isinstance(segment_manifest, dict) else []

    def latest_segment_video(folder: Path) -> str | None:
        if not folder.exists() or not folder.is_dir():
            return None
        videos = [path for path in folder.rglob("*.mp4") if "partial_movie_files" not in path.parts]
        preferred = [path for path in videos if path.name == "GeneratedTeachingScene.mp4"]
        candidates = preferred or videos
        if not candidates:
            return None
        newest = max(candidates, key=lambda path: path.stat().st_mtime)
        return str(newest.resolve())

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        current_video = segment.get("video_path")
        if current_video and Path(str(current_video)).exists():
            continue
        candidates: list[Path] = []
        project_path = segment.get("project_dir")
        if project_path:
            candidates.append(Path(str(project_path)))
        segment_number = segment.get("segment")
        if segment_number:
            try:
                candidates.append(root / "segments" / f"part_{int(segment_number):02d}")
            except (TypeError, ValueError):
                pass
        for candidate in candidates:
            video_path = latest_segment_video(candidate)
            if video_path:
                segment["video_path"] = video_path
                segment["status"] = "rendered"
                break

    return {
        "project_dir": str(root),
        "stages": stage_manifest.get("stages", []) if isinstance(stage_manifest, dict) else [],
        "segments": segments,
        "summary": final_summary if isinstance(final_summary, dict) else {},
    }


@app.get("/project/files")
def project_files(project_dir: str) -> dict[str, object]:
    root = Path(project_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            files.append({"path": rel, "full_path": str(path), "size": path.stat().st_size})
    return {"project_dir": str(root), "files": files}


@app.get("/project/file")
def project_file(path: str) -> dict[str, object]:
    file_path = Path(path).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.suffix.lower() in {".mp4", ".png", ".jpg", ".jpeg", ".webp"}:
        return {"path": str(file_path), "binary": True, "content": ""}
    content = file_path.read_text(encoding="utf-8", errors="replace")
    return {"path": str(file_path), "binary": False, "content": content[:50000]}
