from dataclasses import dataclass, field
from backend.ai.capabilities import ModelAdvancedParameters, ModelCapabilities, ModelProfile
from backend.core.config import Settings

@dataclass(frozen=True)
class ModelRequestConfig:
    """Model settings supplied by UI, .env, or defaults."""

    provider: str
    api_key: str | None
    base_url: str
    model: str
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    parameters: ModelAdvancedParameters = field(default_factory=ModelAdvancedParameters)
    profile_id: str = ""
    provider_name: str = ""

    @classmethod
    def from_profile(cls, profile: ModelProfile) -> "ModelRequestConfig":
        profile = profile.normalized()
        return cls(
            provider="mock" if profile.provider_name == "mock" else "openai-compatible",
            api_key=profile.api_key or None,
            base_url=profile.api_base_url,
            model=profile.model_name,
            capabilities=profile.capabilities,
            parameters=profile.parameters,
            profile_id=profile.id,
            provider_name=profile.provider_name,
        )


def resolve_model_config(settings: Settings, provider: str | None, api_key: str | None, base_url: str | None, model: str | None) -> ModelRequestConfig:
    selected = (provider or settings.default_provider).lower()
    if selected == "openai":
        return ModelRequestConfig("openai-compatible", api_key or settings.openai_api_key, base_url or settings.openai_base_url, model or settings.openai_model, ModelCapabilities(text_generation=True, vision=True, image_upload=True, multimodal_input=True, image_annotation=True, function_calling=True, json_output=True, streaming=True), provider_name="openai")
    if selected == "deepseek":
        return ModelRequestConfig("openai-compatible", api_key or settings.deepseek_api_key, base_url or settings.deepseek_base_url, model or settings.deepseek_model, ModelCapabilities(text_generation=True, json_output=True, streaming=True), provider_name="deepseek")
    if selected == "mock":
        return ModelRequestConfig("mock", None, "", model or "local-mock", ModelCapabilities(text_generation=True, json_output=True), provider_name="mock")
    return ModelRequestConfig("openai-compatible", api_key or None, base_url or "", model or selected, ModelCapabilities(text_generation=True), provider_name=selected)
