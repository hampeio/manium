# Preset schema

The exported JSON object contains:

- `name`: human-readable style name.
- `style_description`: concise evidence-based description.
- `prompt_preset`: operational generation instructions.
- `scene_count`: typical positive integer Scene count.
- `animation_speed`: `快速`, `中等`, or `舒缓`.
- `palette`: ordered color strings.
- `fonts`: ordered font-family strings.
- `workflow`: complete `WorkflowGraph`.
- `example_code`: representative source excerpt.

The Style Library wrapper additionally contains `id`, timestamps, `active_version`,
`analysis`, and immutable `versions`. Each version stores `version`, `created_at`,
`analysis`, and `preset`.

Analysis separates `code_structure`, `visual_style`, and `teaching_rhythm`. Media
items must state whether they were analyzed or only inventoried.
