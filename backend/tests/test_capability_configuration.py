from pathlib import Path

import pytest

from backend.ai.capabilities import ModelCapabilities
from backend.ai.model_config import ModelRequestConfig
from backend.ai.model_router import ModelCapabilityError, ModelRouter, VISION_REQUIRED_MESSAGE
from backend.core.config import Settings
from backend.services.configuration_service import ConfigurationService
from backend.services.segment_media_service import SegmentMediaService


def make_store(tmp_path: Path) -> ConfigurationService:
    settings = Settings(configuration_dir=tmp_path / "config", default_provider="mock")
    return ConfigurationService(settings, tmp_path / "profiles.json")


def test_custom_model_profiles_crud_default_and_import_export(tmp_path: Path):
    store = make_store(tmp_path)
    profile = store.save_model_profile(
        {
            "name": "Local compatible",
            "provider_name": "my-provider",
            "api_base_url": "http://127.0.0.1:9999/v1",
            "api_key": "secret",
            "model_name": "custom-vision",
            "capabilities": {
                "text_generation": True,
                "vision": True,
                "image_upload": True,
                "multimodal_input": True,
                "image_annotation": True,
                "json_output": True,
            },
            "parameters": {"temperature": 0.4, "top_p": 0.8, "max_tokens": 4096},
        }
    )
    store.set_default_model(profile.id)

    selected = store.get_model_profile()
    exported = store.export_data(include_secrets=False)

    assert selected.provider_name == "my-provider"
    assert selected.capabilities.image_annotation
    assert selected.parameters.max_tokens == 4096
    assert exported["default_model_profile_id"] == profile.id
    assert next(item for item in exported["model_profiles"] if item["id"] == profile.id)["api_key"] == ""

    second = make_store(tmp_path / "imported")
    second.import_data(exported)
    assert second.get_model_profile(profile.id).model_name == "custom-vision"
    second.delete_model_profile(profile.id)
    assert all(item["id"] != profile.id for item in second.list_model_profiles()["profiles"])


def test_capabilities_normalize_image_features_when_vision_is_disabled():
    capabilities = ModelCapabilities(
        vision=False,
        image_upload=True,
        multimodal_input=True,
        image_annotation=True,
    ).normalize()

    assert not capabilities.image_upload
    assert not capabilities.multimodal_input
    assert not capabilities.image_annotation


def test_router_rejects_image_before_network_for_non_vision_model(tmp_path: Path):
    image = tmp_path / "image.png"
    image.write_bytes(b"png")
    router = ModelRouter(
        ModelRequestConfig(
            provider="openai-compatible",
            api_key="key",
            base_url="https://example.invalid/v1",
            model="text-only",
            capabilities=ModelCapabilities(text_generation=True, json_output=True),
        )
    )

    with pytest.raises(ModelCapabilityError, match="Vision"):
        router._build_user_content("analyze", image)

    assert VISION_REQUIRED_MESSAGE.startswith("当前所选模型")


def test_request_options_follow_capabilities_and_advanced_parameters():
    config = ModelRequestConfig(
        provider="openai-compatible",
        api_key=None,
        base_url="http://localhost:9999/v1",
        model="local-model",
        capabilities=ModelCapabilities(text_generation=True, json_output=False, streaming=False),
    )
    router = ModelRouter(config)
    payload = {"model": config.model}

    router._apply_request_options(payload, temperature=0.1)

    assert "response_format" not in payload
    assert "stream" not in payload
    assert payload["max_tokens"] == config.parameters.max_tokens


def test_unconfigured_audio_produces_video_only_segment(tmp_path: Path, monkeypatch):
    class NoAudio:
        def is_configured(self):
            return False

    service = SegmentMediaService(NoAudio())
    rendered = tmp_path / "rendered.mp4"
    rendered.write_bytes(b"video")
    monkeypatch.setattr(service, "probe_duration", lambda path: 5.0 if Path(path).suffix == ".mp4" else 0.0)

    assets = service.prepare_segment(
        project_dir=tmp_path,
        segment_id="scene_1",
        rendered_video=rendered,
        narration_text="旁白文本",
        revision=1,
    )

    assert assets["audio_path"] is None
    assert assets["audio_source_path"] is None
    assert assets["timing_adjustment"] == "audio_skipped_not_configured"
    assert Path(assets["preview_video_path"]).exists()

