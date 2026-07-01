from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelCapabilities(BaseModel):
    """Explicit, shared feature flags for one concrete model endpoint."""

    text_generation: bool = True
    vision: bool = False
    image_upload: bool = False
    multimodal_input: bool = False
    image_annotation: bool = False
    function_calling: bool = False
    json_output: bool = False
    streaming: bool = False
    audio: bool = False

    def normalize(self) -> "ModelCapabilities":
        values = self.model_dump()
        if not values["vision"]:
            values.update(image_upload=False, multimodal_input=False, image_annotation=False)
        elif not values["multimodal_input"]:
            values.update(image_upload=False, image_annotation=False)
        elif not values["image_upload"]:
            values["image_annotation"] = False
        return ModelCapabilities(**values)


class ModelAdvancedParameters(BaseModel):
    temperature: float = Field(default=0.25, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    max_tokens: int = Field(default=8192, ge=1)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    extra_headers: dict[str, str] = Field(default_factory=dict)


class CapabilityProbeResult(BaseModel):
    status: Literal["never", "running", "success", "partial", "failed"] = "never"
    tested_at: str | None = None
    message: str = "尚未探测。"
    detected: dict[str, bool] = Field(default_factory=dict)
    details: dict[str, str] = Field(default_factory=dict)


class ModelProfile(BaseModel):
    id: str
    name: str
    provider_name: str
    api_base_url: str
    api_key: str = ""
    model_name: str
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    parameters: ModelAdvancedParameters = Field(default_factory=ModelAdvancedParameters)
    capability_source: Literal["manual", "probe", "builtin"] = "manual"
    probe: CapabilityProbeResult = Field(default_factory=CapabilityProbeResult)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def normalized(self) -> "ModelProfile":
        clone = self.model_copy(deep=True)
        clone.capabilities = clone.capabilities.normalize()
        return clone

    def public_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        payload = self.normalized().model_dump()
        payload["api_key_configured"] = bool(self.api_key)
        if not include_secret:
            payload["api_key"] = ""
        return payload


class AudioProfile(BaseModel):
    id: str
    name: str
    provider_name: str
    api_base_url: str
    api_key: str = ""
    model_name: str = ""
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_parameters: dict[str, Any] = Field(default_factory=dict)
    text_field: str = "text"
    model_field: str = "model"
    response_mode: Literal["binary", "json_base64", "json_url"] = "binary"
    response_audio_field: str = "audio"
    enabled: bool = True
    probe: CapabilityProbeResult = Field(default_factory=CapabilityProbeResult)
    last_call_status: str = "never"
    last_call_message: str = "尚未调用。"
    last_called_at: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def public_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        payload = self.model_dump()
        payload["api_key_configured"] = bool(self.api_key)
        if not include_secret:
            payload["api_key"] = ""
        return payload

