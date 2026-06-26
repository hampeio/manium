import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


class StoryboardScene(BaseModel):
    index: int
    title: str
    narration: str
    visual_plan: str
    estimated_seconds: float = 8.0

    @field_validator("title", "narration", "visual_plan", mode="before")
    @classmethod
    def stringify_text_fields(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @field_validator("estimated_seconds", mode="before")
    @classmethod
    def parse_seconds(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            digits = "".join(char for char in value if char.isdigit() or char == ".")
            if digits:
                return float(digits)
        return 8.0

    @field_validator("index", mode="before")
    @classmethod
    def parse_index(cls, value: Any) -> int:
        return _parse_int(value, 1)


class TeachingPlan(BaseModel):
    image_understanding: str
    teaching_goal: str
    conflict_strategy: str = "????????????"
    scenes: list[StoryboardScene] = Field(min_length=1, max_length=60)
    code_plan: str

    @field_validator("image_understanding", "teaching_goal", "conflict_strategy", mode="before")
    @classmethod
    def stringify_text_fields(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @field_validator("code_plan", mode="before")
    @classmethod
    def stringify_code_plan(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, indent=2)


class StoryboardBatchSpec(BaseModel):
    batch_index: int
    stage: int = Field(ge=1, le=3)
    title: str
    goal: str
    scene_count: int = Field(ge=2, le=8)
    duration_seconds: int = Field(ge=60)

    @field_validator("title", "goal", mode="before")
    @classmethod
    def stringify_text_fields(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @field_validator("batch_index", "stage", "scene_count", "duration_seconds", mode="before")
    @classmethod
    def parse_integer_fields(cls, value: Any) -> int:
        return _parse_int(value, 1)


class GenerationStrategy(BaseModel):
    image_understanding: str
    teaching_goal: str
    conflict_strategy: str = "????????????"
    target_duration_seconds: int = Field(ge=300)
    estimated_scene_count: int = Field(ge=3, le=60)
    ai_call_count: int = Field(ge=3, le=80)
    batches: list[StoryboardBatchSpec] = Field(min_length=3, max_length=12)
    code_plan: str

    @field_validator("image_understanding", "teaching_goal", "conflict_strategy", mode="before")
    @classmethod
    def stringify_text_fields(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @field_validator("code_plan", mode="before")
    @classmethod
    def stringify_code_plan(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, indent=2)

    @field_validator("target_duration_seconds", "estimated_scene_count", "ai_call_count", mode="before")
    @classmethod
    def parse_integer_fields(cls, value: Any) -> int:
        return _parse_int(value, 3)


def _parse_int(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = "".join(char for char in value if char.isdigit())
        if digits:
            return int(digits)
    return fallback


class StoryboardBatchResult(BaseModel):
    scenes: list[StoryboardScene] = Field(min_length=2, max_length=8)


class CodeGenerationResult(BaseModel):
    manim_code: str


class GeneratedAnimation(BaseModel):
    plan: TeachingPlan
    manim_code: str


class RepairResult(BaseModel):
    repaired_code: str
    notes: str
