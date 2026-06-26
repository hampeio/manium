from dataclasses import dataclass
from typing import Literal

from backend.core.config import Settings


ProviderName = Literal["openai", "deepseek", "mock"]


@dataclass(frozen=True)
class ModelRequestConfig:
    """Model settings supplied by UI, .env, or defaults."""

    provider: ProviderName
    api_key: str | None
    base_url: str
    model: str


def resolve_model_config(settings: Settings, provider: str | None, api_key: str | None, base_url: str | None, model: str | None) -> ModelRequestConfig:
    selected = (provider or settings.default_provider).lower()
    if selected == "openai":
        return ModelRequestConfig("openai", api_key or settings.openai_api_key, base_url or settings.openai_base_url, model or settings.openai_model)
    if selected == "deepseek":
        return ModelRequestConfig("deepseek", api_key or settings.deepseek_api_key, base_url or settings.deepseek_base_url, model or settings.deepseek_model)
    return ModelRequestConfig("mock", None, "", model or "local-mock")
