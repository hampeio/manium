---
name: manim-workflow-preset-generator
description: Analyze existing ManimCE projects and optional storyboards, rendered videos, keyframes, audio, or subtitles; infer code structure, visual language, and teaching rhythm; then create, revise, import, export, or version reusable Prompt Presets and workflow templates in the Style Library. Use when learning an author's Manim style, converting a reference project into a reusable preset, evolving an existing style, or applying a learned style to a new course.
---

# Manim Workflow Preset Generator

Create reusable style assets from evidence. Do not generate the requested lesson animation during the learning step.

## Workflow

1. Inventory all supplied files. Require at least one `.py` source file. Treat video, image, audio, storyboard, and subtitle files as optional evidence.
2. Detect the framework before analysis:
   - `from manim import` means ManimCE.
   - `from manimlib import` means ManimGL; report it and avoid applying ManimCE-only assumptions.
3. Run `scripts/analyze_project.py <project-or-file> --name "<style name>" --output <preset.json>` from the repository root for deterministic code analysis.
4. Review the report against the source. Distinguish measured facts from inferred labels and preserve confidence values.
5. Produce a preset conforming to `references/preset-schema.md`.
6. Save it through the application's Style Library. When updating a known style, append a version instead of overwriting history.
7. Apply a preset by prefixing the new lesson request with `prompt_preset` and by loading its `workflow`.

## Analysis Requirements

Capture:

- Scene classes, lifecycle methods, helper functions, construction order, common mobjects, VGroup/Group organization, layouts, camera operations, updaters, and animation sequences.
- Creation, fade, transform, matching-transform, grouping, timing, and wait patterns.
- Background, palette, typography, font-size range, density, whitespace, emphasis, and recurring composition.
- Estimated duration, average animation and wait length, reveal-versus-transform balance, and teaching cadence.
- Evidence coverage and parse errors.

Never claim that metadata-only video or audio inspection measured visual or acoustic qualities. If frame or waveform analysis is unavailable, mark that evidence as metadata-only.

## Preset Quality

Write `prompt_preset` as operational constraints, not vague adjectives. Include:

- visual system and concept-to-color consistency;
- layout rules and whitespace;
- preferred objects and animation families;
- Scene count and sequencing;
- animation duration and reveal pattern;
- prohibited failure modes;
- ManimCE compatibility requirements.

Keep the example code short and representative. Store the full generated workflow graph in the preset so it can be loaded directly.

## Continuous Learning

When the user supplies a revised project:

1. Select the existing style ID.
2. Re-run analysis on the complete new evidence set.
3. Compare the new analysis with the active version.
4. Summarize added, removed, and changed patterns.
5. Append a new version and retain all older records.
6. Roll back by switching the active version; never delete history as part of rollback.

## Application Integration

The local application exposes:

- `POST /style-library/analyze`
- `GET /style-library`
- `GET /style-library/{style_id}`
- `PUT /style-library/{style_id}`
- `POST /style-library/{style_id}/rollback/{version}`
- `POST /style-library/import`

Use these endpoints only when the user asks to persist or apply the result. For analysis-only requests, return the generated JSON without mutating the library.
