import json
from pathlib import Path
from typing import Any

import backend.ai.model_router as model_router
import backend.ai.prompts as prompts


PROMPT_NAMES = [
    "SYSTEM_PROMPT",
    "PLAN_AND_CODE_PROMPT",
    "GENERATION_STRATEGY_PROMPT",
    "STORYBOARD_BATCH_PROMPT",
    "CODE_FROM_PLAN_PROMPT",
    "SEGMENT_CODE_PROMPT",
    "REPAIR_PROMPT",
]

OVERRIDE_PATH = Path("prompt_overrides.json")


def get_prompt_values() -> dict[str, str]:
    """Return the currently active prompt templates."""

    return {name: str(getattr(prompts, name)) for name in PROMPT_NAMES}


def load_prompt_overrides(path: Path = OVERRIDE_PATH) -> dict[str, str]:
    """Load saved prompt overrides and apply them to prompt modules."""

    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    values = raw.get("prompts", raw) if isinstance(raw, dict) else {}
    updates = {
        name: str(values[name])
        for name in PROMPT_NAMES
        if name in values
        and str(values[name]).strip()
        and not _is_legacy_english_prompt(str(values[name]))
    }
    apply_prompt_overrides(updates, save=False, path=path)
    return updates


def apply_prompt_overrides(updates: dict[str, Any], *, save: bool = True, path: Path = OVERRIDE_PATH) -> dict[str, str]:
    """Apply editable prompt templates at runtime and optionally persist them."""

    clean_updates = {
        name: str(value)
        for name, value in updates.items()
        if name in PROMPT_NAMES and isinstance(value, str) and value.strip()
    }
    for name, value in clean_updates.items():
        setattr(prompts, name, value)
        if hasattr(model_router, name):
            setattr(model_router, name, value)

    if save:
        path.write_text(json.dumps({"prompts": get_prompt_values()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_prompt_values()


def _is_legacy_english_prompt(value: str) -> bool:
    """Prevents old bundled English defaults from overriding Chinese prompts."""

    legacy_markers = (
        "Output strict JSON only",
        "Generate runnable ManimCE code",
        "You are a senior teaching-animation director",
        "Repair this Manim Community Edition code",
    )
    return any(marker in value for marker in legacy_markers)
