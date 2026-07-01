from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from backend.ai.capabilities import (
    AudioProfile,
    ModelCapabilities,
    ModelProfile,
    utc_now_iso,
)
from backend.core.config import Settings


class ConfigurationService:
    """Persistent model/audio profiles, independent from provider-specific code."""

    def __init__(self, settings: Settings, path: Path | None = None):
        self.settings = settings
        self.path = path or settings.configuration_dir / "provider_profiles.json"
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(self._seed_data())

    def _seed_data(self) -> dict[str, Any]:
        profiles = [
            ModelProfile(
                id="builtin-mock",
                name="本地 Mock",
                provider_name="mock",
                api_base_url="",
                model_name="local-mock",
                capabilities=ModelCapabilities(text_generation=True, json_output=True),
                capability_source="builtin",
            ),
            ModelProfile(
                id="builtin-openai",
                name="OpenAI 默认配置",
                provider_name="openai-compatible",
                api_base_url=self.settings.openai_base_url,
                api_key=self.settings.openai_api_key or "",
                model_name=self.settings.openai_model,
                capabilities=ModelCapabilities(
                    text_generation=True,
                    vision=True,
                    image_upload=True,
                    multimodal_input=True,
                    image_annotation=True,
                    function_calling=True,
                    json_output=True,
                    streaming=True,
                    audio=False,
                ),
                capability_source="builtin",
            ),
            ModelProfile(
                id="builtin-deepseek",
                name="DeepSeek 默认配置",
                provider_name="openai-compatible",
                api_base_url=self.settings.deepseek_base_url,
                api_key=self.settings.deepseek_api_key or "",
                model_name=self.settings.deepseek_model,
                capabilities=ModelCapabilities(
                    text_generation=True,
                    json_output=True,
                    streaming=True,
                ),
                capability_source="builtin",
            ),
        ]
        default_map = {"openai": "builtin-openai", "deepseek": "builtin-deepseek", "mock": "builtin-mock"}
        return {
            "version": 1,
            "default_model_profile_id": default_map.get(str(self.settings.default_provider), "builtin-mock"),
            "default_audio_profile_id": None,
            "model_profiles": [profile.model_dump() for profile in profiles],
            "audio_profiles": [],
        }

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        with self._lock:
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.path)

    def list_model_profiles(self, *, include_secrets: bool = False) -> dict[str, Any]:
        data = self._read()
        return {
            "default_id": data.get("default_model_profile_id"),
            "profiles": [ModelProfile.model_validate(item).public_dict(include_secret=include_secrets) for item in data.get("model_profiles", [])],
        }

    def get_model_profile(self, profile_id: str | None = None) -> ModelProfile:
        data = self._read()
        selected = profile_id or data.get("default_model_profile_id")
        item = next((item for item in data.get("model_profiles", []) if item.get("id") == selected), None)
        if not item:
            raise ValueError("找不到模型配置。")
        return ModelProfile.model_validate(item).normalized()

    def save_model_profile(self, payload: dict[str, Any]) -> ModelProfile:
        data = self._read()
        profiles = data.setdefault("model_profiles", [])
        profile_id = str(payload.get("id") or f"model-{uuid4().hex[:12]}")
        current = next((item for item in profiles if item.get("id") == profile_id), None)
        merged = {**(current or {}), **payload, "id": profile_id, "updated_at": utc_now_iso()}
        if current and not payload.get("api_key"):
            merged["api_key"] = current.get("api_key", "")
        profile = ModelProfile.model_validate(merged).normalized()
        if current:
            profiles[profiles.index(current)] = profile.model_dump()
        else:
            profiles.append(profile.model_dump())
        if payload.get("is_default") or not data.get("default_model_profile_id"):
            data["default_model_profile_id"] = profile.id
        self._write(data)
        return profile

    def delete_model_profile(self, profile_id: str) -> None:
        data = self._read()
        profiles = data.get("model_profiles", [])
        remaining = [item for item in profiles if item.get("id") != profile_id]
        if len(remaining) == len(profiles):
            raise ValueError("找不到模型配置。")
        if not remaining:
            raise ValueError("至少保留一个模型配置。")
        data["model_profiles"] = remaining
        if data.get("default_model_profile_id") == profile_id:
            data["default_model_profile_id"] = remaining[0]["id"]
        self._write(data)

    def set_default_model(self, profile_id: str) -> ModelProfile:
        profile = self.get_model_profile(profile_id)
        data = self._read()
        data["default_model_profile_id"] = profile.id
        self._write(data)
        return profile

    def list_audio_profiles(self, *, include_secrets: bool = False) -> dict[str, Any]:
        data = self._read()
        return {
            "default_id": data.get("default_audio_profile_id"),
            "profiles": [AudioProfile.model_validate(item).public_dict(include_secret=include_secrets) for item in data.get("audio_profiles", [])],
        }

    def get_audio_profile(self, profile_id: str | None = None) -> AudioProfile | None:
        data = self._read()
        selected = profile_id or data.get("default_audio_profile_id")
        if not selected:
            return None
        item = next((item for item in data.get("audio_profiles", []) if item.get("id") == selected), None)
        return AudioProfile.model_validate(item) if item else None

    def save_audio_profile(self, payload: dict[str, Any]) -> AudioProfile:
        data = self._read()
        profiles = data.setdefault("audio_profiles", [])
        profile_id = str(payload.get("id") or f"audio-{uuid4().hex[:12]}")
        current = next((item for item in profiles if item.get("id") == profile_id), None)
        merged = {**(current or {}), **payload, "id": profile_id, "updated_at": utc_now_iso()}
        if current and not payload.get("api_key"):
            merged["api_key"] = current.get("api_key", "")
        profile = AudioProfile.model_validate(merged)
        if current:
            profiles[profiles.index(current)] = profile.model_dump()
        else:
            profiles.append(profile.model_dump())
        if payload.get("is_default") or not data.get("default_audio_profile_id"):
            data["default_audio_profile_id"] = profile.id
        self._write(data)
        return profile

    def delete_audio_profile(self, profile_id: str) -> None:
        data = self._read()
        profiles = data.get("audio_profiles", [])
        remaining = [item for item in profiles if item.get("id") != profile_id]
        if len(remaining) == len(profiles):
            raise ValueError("找不到音频配置。")
        data["audio_profiles"] = remaining
        if data.get("default_audio_profile_id") == profile_id:
            data["default_audio_profile_id"] = remaining[0]["id"] if remaining else None
        self._write(data)

    def set_default_audio(self, profile_id: str) -> AudioProfile:
        profile = self.get_audio_profile(profile_id)
        if not profile:
            raise ValueError("找不到音频配置。")
        data = self._read()
        data["default_audio_profile_id"] = profile.id
        self._write(data)
        return profile

    def update_audio_status(self, profile_id: str, *, status: str, message: str, probe: dict[str, Any] | None = None) -> None:
        data = self._read()
        for item in data.get("audio_profiles", []):
            if item.get("id") == profile_id:
                item.update(last_call_status=status, last_call_message=message, last_called_at=utc_now_iso())
                if probe is not None:
                    item["probe"] = probe
                self._write(data)
                return

    def import_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        for item in payload.get("model_profiles", payload.get("models", [])):
            self.save_model_profile(dict(item))
        for item in payload.get("audio_profiles", payload.get("audio", [])):
            self.save_audio_profile(dict(item))
        if payload.get("default_model_profile_id"):
            self.set_default_model(str(payload["default_model_profile_id"]))
        if payload.get("default_audio_profile_id"):
            self.set_default_audio(str(payload["default_audio_profile_id"]))
        return self.export_data(include_secrets=False)

    def export_data(self, *, include_secrets: bool = False) -> dict[str, Any]:
        data = self._read()
        return {
            "version": data.get("version", 1),
            "default_model_profile_id": data.get("default_model_profile_id"),
            "default_audio_profile_id": data.get("default_audio_profile_id"),
            "model_profiles": [ModelProfile.model_validate(item).public_dict(include_secret=include_secrets) for item in data.get("model_profiles", [])],
            "audio_profiles": [AudioProfile.model_validate(item).public_dict(include_secret=include_secrets) for item in data.get("audio_profiles", [])],
        }
