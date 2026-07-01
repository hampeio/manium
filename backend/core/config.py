from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from .env without exposing secrets in logs."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Manim 教学动画生成器"
    host: str = "127.0.0.1"
    port: int = 8765
    generated_projects_dir: Path = Field(default=Path("generated_projects"))
    configuration_dir: Path = Field(default=Path("config"))
    default_provider: Literal["openai", "deepseek", "mock"] = "deepseek"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    xunfei_tts_enabled: bool = False
    xunfei_app_id: str | None = None
    xunfei_api_key: str | None = None
    xunfei_api_secret: str | None = None
    xunfei_tts_url: str = "wss://tts-api.xfyun.cn/v2/tts"
    xunfei_tts_voice: str = "x4_xiaoyan"

    fish_tts_enabled: bool = False
    fish_tts_api_key: str | None = None
    fish_tts_url: str = "https://api.fish.audio/v1/tts"
    fish_tts_reference_id: str = "5b5564a32f924a4b9eb8cccea278b7a1"
    fish_tts_model: str = "s2-pro"
    fish_tts_speed: float = 1.0
    fish_tts_format: str = "mp3"

    manim_scene_name: str = "GeneratedTeachingScene"
    manim_command: str = "python -m manim"


@lru_cache
def get_settings() -> Settings:
    return Settings()
