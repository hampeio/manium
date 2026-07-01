import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.ai.model_config import ModelRequestConfig, resolve_model_config
from backend.ai.model_router import ModelRouter, VISION_REQUIRED_MESSAGE
from backend.ai.prompt_store import apply_prompt_overrides, get_prompt_values, load_prompt_overrides
from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.services.generation_service import GenerationService
from backend.services.annotation_service import AnnotationService
from backend.services.capability_probe_service import CapabilityProbeService
from backend.services.configuration_service import ConfigurationService
from backend.services.project_manager import ProjectManager
from backend.services.task_registry import TaskRegistry
from backend.services.style_library_service import StyleLibraryService
from backend.workflow.executor import WorkflowExecutor
from backend.workflow.node_registry import list_node_definitions, register_custom_node
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
task_registry = TaskRegistry(settings.generated_projects_dir)
workflow_executor = WorkflowExecutor(generation_service, project_manager)
annotation_service = AnnotationService()
configuration_service = ConfigurationService(settings)
capability_probe_service = CapabilityProbeService()
style_library_service = StyleLibraryService(settings.configuration_dir / "style_library")


def _resolve_request_model(
    model_profile_id: str,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
) -> ModelRequestConfig:
    if model_profile_id:
        return ModelRequestConfig.from_profile(configuration_service.get_model_profile(model_profile_id))
    return resolve_model_config(settings, provider or None, api_key or None, base_url or None, model or None)


def _require_image_capability(config: ModelRequestConfig, has_image: bool) -> None:
    if not has_image:
        return
    capabilities = config.capabilities.normalize()
    if not (capabilities.vision and capabilities.image_upload and capabilities.multimodal_input):
        raise HTTPException(status_code=400, detail=VISION_REQUIRED_MESSAGE)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/configurations")
def configurations_export(include_secrets: bool = False) -> dict[str, object]:
    return configuration_service.export_data(include_secrets=include_secrets)


@app.post("/configurations/import")
def configurations_import(payload: dict[str, object]) -> dict[str, object]:
    try:
        return configuration_service.import_data(payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/model-configs")
def model_configs() -> dict[str, object]:
    return configuration_service.list_model_profiles()


@app.post("/model-configs")
def model_configs_save(payload: dict[str, object]) -> dict[str, object]:
    try:
        profile = configuration_service.save_model_profile(payload)
        return {"profile": profile.public_dict(), **configuration_service.list_model_profiles()}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/model-configs/{profile_id}")
def model_configs_delete(profile_id: str) -> dict[str, object]:
    try:
        configuration_service.delete_model_profile(profile_id)
        return configuration_service.list_model_profiles()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/model-configs/{profile_id}/default")
def model_configs_default(profile_id: str) -> dict[str, object]:
    try:
        profile = configuration_service.set_default_model(profile_id)
        return {"profile": profile.public_dict(), **configuration_service.list_model_profiles()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/model-configs/{profile_id}/probe")
async def model_configs_probe(profile_id: str) -> dict[str, object]:
    try:
        profile = configuration_service.get_model_profile(profile_id)
        capabilities, probe = await capability_probe_service.probe(profile)
        profile.capabilities = capabilities
        profile.capability_source = "probe"
        profile.probe = probe
        saved = configuration_service.save_model_profile(profile.model_dump())
        return {"profile": saved.public_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/model-configs/{profile_id}/capabilities")
def model_capabilities(profile_id: str) -> dict[str, object]:
    try:
        profile = configuration_service.get_model_profile(profile_id)
        return {"profile_id": profile.id, "capabilities": profile.capabilities.model_dump(), "probe": profile.probe.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/audio-configs")
def audio_configs() -> dict[str, object]:
    return configuration_service.list_audio_profiles()


@app.post("/audio-configs")
def audio_configs_save(payload: dict[str, object]) -> dict[str, object]:
    try:
        profile = configuration_service.save_audio_profile(payload)
        return {"profile": profile.public_dict(), **configuration_service.list_audio_profiles()}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/audio-configs/{profile_id}")
def audio_configs_delete(profile_id: str) -> dict[str, object]:
    try:
        configuration_service.delete_audio_profile(profile_id)
        return configuration_service.list_audio_profiles()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/audio-configs/{profile_id}/default")
def audio_configs_default(profile_id: str) -> dict[str, object]:
    try:
        profile = configuration_service.set_default_audio(profile_id)
        return {"profile": profile.public_dict(), **configuration_service.list_audio_profiles()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/audio-configs/{profile_id}/test")
async def audio_configs_test(profile_id: str) -> dict[str, object]:
    try:
        profile = configuration_service.get_audio_profile(profile_id)
        if not profile:
            raise ValueError("找不到音频配置。")
        output = settings.configuration_dir / "audio_tests" / f"{profile.id}.audio"
        result = await asyncio.to_thread(generation_service.tts_service.test_audio_profile, profile, output)
        return {"success": result.status == "success", "status": result.status, "message": result.message, "error": result.error}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/prompts")
def prompts_get() -> dict[str, object]:
    return {"prompts": get_prompt_values()}


@app.post("/prompts")
async def prompts_post(payload: dict[str, object]) -> dict[str, object]:
    values = payload.get("prompts", payload)
    if not isinstance(values, dict):
        raise HTTPException(status_code=400, detail="提示词数据格式无效。")
    return {"prompts": apply_prompt_overrides(values)}


@app.get("/style-library")
def style_library_list() -> dict[str, object]:
    return style_library_service.list_styles()


@app.get("/style-library/{style_id}")
def style_library_get(style_id: str, version: int | None = None) -> dict[str, object]:
    try:
        return style_library_service.get_style(style_id, version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/style-library/analyze")
async def style_library_analyze(
    files: list[UploadFile] = File(...),
    style_name: str = Form(default=""),
    description: str = Form(default=""),
    existing_style_id: str = Form(default=""),
    model_profile_id: str = Form(default=""),
    use_ai: bool = Form(default=True),
) -> dict[str, object]:
    try:
        payload = [(item.filename or "unnamed", await item.read()) for item in files]
        style = style_library_service.analyze(
            style_name=style_name.strip(),
            description=description.strip(),
            existing_style_id=existing_style_id.strip(),
            files=payload,
        )
        if not use_ai:
            return style
        profile = configuration_service.get_model_profile(model_profile_id.strip() or None)
        model_config = ModelRequestConfig.from_profile(profile)
        image_path: Path | None = None
        image_item = next(
            ((name, data) for name, data in payload if Path(name).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}),
            None,
        )
        if image_item and model_config.capabilities.normalize().vision:
            image_dir = settings.configuration_dir / "style_library" / "_model_inputs"
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{style['id']}{Path(image_item[0]).suffix.lower()}"
            image_path.write_bytes(image_item[1])
        try:
            router = ModelRouter(model_config, trace_dir=settings.configuration_dir / "style_library" / "ai_traces")
            result = await router.analyze_manim_style(style["analysis"], image_path)
            return style_library_service.apply_model_analysis(style["id"], result, model_config.model)
        except Exception as exc:
            return style_library_service.mark_model_fallback(style["id"], str(exc), model_config.model)
        finally:
            if image_path and image_path.exists():
                image_path.unlink()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/style-library/{style_id}")
def style_library_update(style_id: str, payload: dict[str, object]) -> dict[str, object]:
    try:
        return style_library_service.save_preset(style_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/style-library/{style_id}/rollback/{version}")
def style_library_rollback(style_id: str, version: int) -> dict[str, object]:
    try:
        return style_library_service.rollback(style_id, version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/style-library/import")
def style_library_import(payload: dict[str, object]) -> dict[str, object]:
    return style_library_service.import_style(payload)


@app.post("/generate")
async def generate(
    prompt: str = Form(default=""),
    model_profile_id: str = Form(default=""),
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
    model_config = _resolve_request_model(model_profile_id, provider, api_key, base_url, model)
    _require_image_capability(model_config, image is not None and bool(image.filename))
    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    image_path = await active_manager.save_upload(project_dir, image)
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
    model_profile_id: str = Form(default=""),
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
    model_config = _resolve_request_model(model_profile_id, provider, api_key, base_url, model)
    _require_image_capability(model_config, image is not None and bool(image.filename))
    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    image_path = await active_manager.save_upload(project_dir, image)
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
    model_profile_id: str = Form(default=""),
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
        raise HTTPException(status_code=404, detail="找不到源项目。")
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
    model_config = _resolve_request_model(model_profile_id, provider, api_key, base_url, model)
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
    model_profile_id: str = Form(default=""),
    provider: str = Form(default=""),
    api_key: str = Form(default=""),
    base_url: str = Form(default=""),
    model: str = Form(default=""),
    quality: str = Form(default="preview_720p"),
    use_project_image: bool = Form(default=False),
) -> dict[str, object]:
    source_dir = Path(source_project_dir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="找不到源项目。")
    if not segment_id:
        raise HTTPException(status_code=400, detail="必须指定要修改的片段。")
    model_config = _resolve_request_model(model_profile_id, provider, api_key, base_url, model)
    reference_image = next(source_dir.glob("inputs/uploaded_image.*"), None) if use_project_image else None
    _require_image_capability(model_config, reference_image is not None)
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
                reference_image=reference_image,
                progress=lambda message: task_registry.log(task.task_id, message),
                partial_update=lambda partial: task_registry.update_partial(task.task_id, partial),
            )
            task_registry.complete(task.task_id, result)
        except Exception as exc:
            task_registry.fail(task.task_id, str(exc))

    asyncio.create_task(run_job())
    return {"task_id": task.task_id, "project_dir": str(source_dir), "state": "queued"}


@app.get("/project/segment-code")
def project_segment_code(project_dir: str, segment_id: str) -> dict[str, object]:
    source_dir = Path(project_dir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="找不到项目。")
    try:
        return generation_service.get_segment_code_info(project_dir=source_dir, segment_id=segment_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/render_segment_code_async")
async def render_segment_code_async(
    project_dir: str = Form(default=""),
    segment_id: str = Form(default=""),
    manim_code: str = Form(default=""),
    quality: str = Form(default="preview_720p"),
    timing_policy: str = Form(default="auto_audio"),
    manual_duration: float = Form(default=0),
) -> dict[str, object]:
    source_dir = Path(project_dir).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="找不到项目。")
    if not segment_id or not manim_code.strip():
        raise HTTPException(status_code=400, detail="必须选择片段并提供 Manim 代码。")
    task = task_registry.create(str(source_dir))

    async def run_job() -> None:
        task_registry.start(task.task_id)
        try:
            result = await generation_service.render_segment_code(
                project_dir=source_dir,
                segment_id=segment_id,
                manim_code=manim_code,
                quality=quality,
                timing_policy=timing_policy,
                manual_duration=manual_duration or None,
                progress=lambda message: task_registry.log(task.task_id, message),
                partial_update=lambda partial: task_registry.update_partial(task.task_id, partial),
            )
            task_registry.complete(task.task_id, result)
        except Exception as exc:
            task_registry.fail(task.task_id, str(exc))

    asyncio.create_task(run_job())
    return {"task_id": task.task_id, "project_dir": str(source_dir), "state": "queued"}


@app.post("/compose_project_async")
async def compose_project_async(project_dir: str = Form(default="")) -> dict[str, object]:
    """Starts final composition only after an explicit user request."""

    source_dir = Path(project_dir).resolve()
    if not project_dir or not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="Project directory not found.")
    task = task_registry.create(str(source_dir))

    async def run_job() -> None:
        task_registry.start(task.task_id)
        try:
            result = await generation_service.compose_project(
                project_dir=source_dir,
                progress=lambda message: task_registry.log(task.task_id, message),
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
        raise HTTPException(status_code=404, detail="找不到任务。")
    return task


@app.get("/tasks")
def list_tasks() -> dict[str, object]:
    return {"tasks": task_registry.list_dicts()}


@app.post("/tasks/{task_id}/pause")
def pause_task(task_id: str) -> dict[str, object]:
    if not task_registry.pause(task_id):
        raise HTTPException(status_code=404, detail="找不到任务或当前任务无法暂停。")
    return {"task_id": task_id, "state": "paused"}


@app.post("/tasks/{task_id}/resume")
def resume_task(task_id: str) -> dict[str, object]:
    if not task_registry.resume(task_id):
        raise HTTPException(status_code=404, detail="找不到任务或当前任务无法继续。")
    return {"task_id": task_id, "state": "running"}


@app.get("/workflow/node-definitions")
def workflow_node_definitions() -> dict[str, object]:
    return {"nodes": [definition.model_dump() for definition in list_node_definitions()]}


@app.post("/workflow/custom-nodes")
async def workflow_upload_custom_node(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="自定义节点必须是 JSON 文件。")
    raw = await file.read()
    if len(raw) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="节点配置文件不能超过 1MB。")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("节点配置根对象必须是 JSON 对象。")
        definition = register_custom_node(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"JSON 无法解析：{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "自定义节点已加入节点库。", "node": definition.model_dump()}


@app.get("/workflow/templates")
def workflow_templates() -> dict[str, object]:
    return {"templates": list_templates()}


@app.get("/workflow/templates/{template_id}")
def workflow_template(template_id: str) -> dict[str, object]:
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="找不到工作流模板。")
    return template.model_dump()


@app.post("/workflow/validate")
async def workflow_validate(workflow: WorkflowGraph) -> dict[str, object]:
    return validate_workflow(workflow).model_dump()


@app.post("/workflow/run_async")
async def workflow_run_async(
    workflow: WorkflowGraph,
    model_profile_id: str = "",
    provider: str = "",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    quality: str = "low",
    output_dir: str = "",
) -> dict[str, object]:
    model_config = _resolve_request_model(model_profile_id, provider, api_key, base_url, model)
    uses_image_nodes = any(node.type in {"InputImageNode", "ImagePreprocessNode", "ImageUnderstandNode"} for node in workflow.nodes)
    _require_image_capability(model_config, uses_image_nodes)
    active_manager = ProjectManager(Path(output_dir)) if output_dir else project_manager
    project_dir = active_manager.create_project()
    task = task_registry.create(str(project_dir.resolve()))

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
        raise HTTPException(status_code=404, detail="找不到视频。")
    return FileResponse(video_path, media_type="video/mp4")


@app.head("/video")
def video_head(path: str) -> FileResponse:
    return video(path)


@app.get("/project/annotations")
def project_annotations(project_dir: str) -> dict[str, object]:
    try:
        annotations = annotation_service.load(Path(project_dir))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"project_dir": str(Path(project_dir).resolve()), "annotations": annotations}


@app.post("/project/annotations")
def create_project_annotation(payload: dict[str, object]) -> dict[str, object]:
    project_dir = str(payload.pop("project_dir", ""))
    model_profile_id = str(payload.pop("model_profile_id", ""))
    if not project_dir:
        raise HTTPException(status_code=400, detail="project_dir is required.")
    shape_data = payload.get("shape_data") if isinstance(payload.get("shape_data"), dict) else {}
    if shape_data.get("target_kind") == "image":
        profile = configuration_service.get_model_profile(model_profile_id or None)
        if not profile.capabilities.normalize().image_annotation:
            raise HTTPException(status_code=400, detail=VISION_REQUIRED_MESSAGE)
    try:
        annotation = annotation_service.create(Path(project_dir), payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"annotation": annotation}


@app.put("/project/annotations/{annotation_id}")
def update_project_annotation(annotation_id: str, payload: dict[str, object]) -> dict[str, object]:
    project_dir = str(payload.pop("project_dir", ""))
    model_profile_id = str(payload.pop("model_profile_id", ""))
    if not project_dir:
        raise HTTPException(status_code=400, detail="project_dir is required.")
    shape_data = payload.get("shape_data") if isinstance(payload.get("shape_data"), dict) else {}
    if shape_data.get("target_kind") == "image":
        profile = configuration_service.get_model_profile(model_profile_id or None)
        if not profile.capabilities.normalize().image_annotation:
            raise HTTPException(status_code=400, detail=VISION_REQUIRED_MESSAGE)
    try:
        annotation = annotation_service.update(Path(project_dir), annotation_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return {"annotation": annotation}


@app.delete("/project/annotations/{annotation_id}")
def delete_project_annotation(annotation_id: str, project_dir: str) -> dict[str, object]:
    try:
        deleted = annotation_service.delete(Path(project_dir), annotation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return {"deleted": True, "id": annotation_id}


@app.get("/projects/root")
def projects_root(root_dir: str = "", include_unfinished: bool = False) -> dict[str, object]:
    """Lists projects below an output root, optionally including unfinished work."""

    root = Path(root_dir).resolve() if root_dir else settings.generated_projects_dir.resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail="根文件夹不存在。")

    projects: list[dict[str, object]] = []
    for project_dir in sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        video_path = _finished_project_video(project_dir)
        if not video_path and not include_unfinished:
            continue
        prompt_path = project_dir / "inputs" / "user_prompt.txt"
        prompt = prompt_path.read_text(encoding="utf-8", errors="replace").strip() if prompt_path.exists() else ""
        projects.append(
            {
                "name": project_dir.name,
                "project_dir": str(project_dir.resolve()),
                "video_path": str(video_path.resolve()) if video_path else None,
                "title": prompt.splitlines()[0][:80] if prompt else project_dir.name,
                "modified_at": project_dir.stat().st_mtime,
                "size": video_path.stat().st_size if video_path else 0,
                "status": "已完成" if video_path else "未完成",
            }
        )
    return {"root_dir": str(root), "projects": projects}


def _finished_project_video(project_dir: Path) -> Path | None:
    """Selects the user-facing final video and excludes Manim cache artifacts."""

    summary_path = project_dir / "final_summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8", errors="replace"))
            if summary.get("compose_status") in {"awaiting_user", "stale"}:
                return None
        except json.JSONDecodeError:
            pass

    candidates = [
        project_dir / "outputs" / "final" / "course_final.mp4",
        project_dir / "outputs" / "animation_with_audio.mp4",
        project_dir / "outputs" / "animation.mp4",
        project_dir / "stitched" / "course_final.mp4",
    ]
    return next((path for path in candidates if path.exists() and path.is_file()), None)


@app.get("/project/status")
def project_status(project_dir: str) -> dict[str, object]:
    root = Path(project_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail="找不到项目。")

    def read_json(name: str, default: object) -> object:
        path = root / name
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))

    stage_manifest = read_json("stage_manifest.json", {})
    segment_manifest = read_json("segment_manifest.json", {})
    final_summary = read_json("final_summary.json", {})
    segments = segment_manifest.get("segments", []) if isinstance(segment_manifest, dict) else []
    finished_video = _finished_project_video(root)
    final_video_path = str(finished_video.resolve()) if finished_video else None
    if final_video_path and isinstance(final_summary, dict):
        final_summary.setdefault("video_path", final_video_path)
        final_summary.setdefault("output_video_path", final_video_path)
    stages = stage_manifest.get("stages", []) if isinstance(stage_manifest, dict) else []
    if final_video_path:
        for stage in stages:
            if isinstance(stage, dict) and stage.get("is_stitching_stage"):
                stage["status"] = "stitched"

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
        if final_video_path:
            segment["final_video_path"] = final_video_path

    return {
        "project_dir": str(root),
        "stages": stages,
        "segments": segments,
        "summary": final_summary if isinstance(final_summary, dict) else {},
    }


@app.get("/project/files")
def project_files(project_dir: str) -> dict[str, object]:
    root = Path(project_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail="找不到项目。")
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
        raise HTTPException(status_code=404, detail="找不到文件。")
    if file_path.suffix.lower() in {".mp4", ".png", ".jpg", ".jpeg", ".webp"}:
        return {"path": str(file_path), "binary": True, "content": ""}
    content = file_path.read_text(encoding="utf-8", errors="replace")
    return {"path": str(file_path), "binary": False, "content": content[:50000]}
