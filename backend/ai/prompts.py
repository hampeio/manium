MANIMCE_CODE_RULES = """
ManimCE hard rules, derived from the local manimce-best-practices skill:
1. Use Manim Community Edition only: exactly `from manim import *`; never use `manimlib`, `InteractiveScene`, or ManimGL APIs.
2. Define exactly one renderable class: `class GeneratedTeachingScene(Scene):` with a `construct(self)` method.
3. Return raw Python source inside JSON. Do not wrap code in Markdown fences.
4. Use stable ManimCE primitives: Scene, Text, VGroup, Group, Dot, Line, Arrow, DashedLine, Brace, Rectangle, Circle, Square, Polygon, and use Axes/NumberPlane only when the storyboard explicitly requires coordinates, graphs, vectors, functions, or math/physics measurement.
5. Use stable animations: Create, Write, FadeIn, FadeOut, GrowArrow, Transform, ReplacementTransform, TransformFromCopy, Circumscribe, LaggedStart, Succession.
6. Use `self.play(...)` and `self.wait(...)`; keep run_time values modest, usually 0.5 to 2.0 seconds.
7. Use positioning helpers: move_to, shift, next_to, to_edge, to_corner, arrange, arrange_in_grid. Do not manually guess screen pixels.
8. For coordinate scenes only, use Axes/NumberPlane with `axes.c2p(x, y)` or `plane.c2p(x, y)` for all plotted points. Do not use coordinate axes as a generic fallback for non-math topics.
9. For arrows and lines, pass explicit start/end points. For vectors, prefer `Vector([x, y, 0])` or an Arrow from ORIGIN.
10. Use Chinese for all teaching text: storyboard titles, narration, subtitles, on-screen labels, and summary text must be Chinese.
10a. For Chinese Manim `Text`, specify `font="Microsoft YaHei"` whenever possible. Keep labels short to avoid clutter.
11. Do not use MathTex by default. The first Windows build may not have LaTeX installed. Show formula-like content with Text, for example `Text("A x = b", font_size=34)`.
12. If MathTex already appears in code during repair and LaTeX-related errors appear, replace MathTex with Text immediately.
12a. Do not call `axes.add_coordinates()`, `axis.add_numbers()`, `DecimalNumber`, or `Integer`; these can trigger LaTeX/Tex rendering on minimal Windows installs.
12b. Do not call `axes.get_x_axis_label("x")` or `axes.get_y_axis_label("y")` with strings. Use `Text("x").next_to(axes.x_axis.get_end(), DOWN)` and `Text("y").next_to(axes.y_axis.get_end(), LEFT)` instead.
13. Do not depend on external images, SVG files, plugins, internet access, audio, or TTS inside Manim code. The app will add audio after rendering.
14. Keep each screen uncluttered: at most a title, one main diagram, one formula, and a few labels.
15. Set a dark background using `self.camera.background_color = "#111827"` or similar.
16. Avoid fragile APIs and speculative methods. If unsure, use simple mobjects and simple transformations.
17. The code must run with `python -m manim -qm scene.py GeneratedTeachingScene`.
"""

SYSTEM_PROMPT = f"""You are a senior teaching-animation director and Manim Community Edition engineer.
You must plan before code. The style should feel like 3Blue1Brown: dark background, clear diagrams, colored formulas, smooth transformations, little text.
All generated teaching content must be Chinese unless a formula or variable name naturally needs Latin letters.
Output strict JSON only. No Markdown.

{MANIMCE_CODE_RULES}
"""

PLAN_AND_CODE_PROMPT = """Generate a teaching animation plan and runnable ManimCE code from the input.

Required JSON shape:
- top-level object with keys: plan, manim_code
- plan object keys: image_understanding, teaching_goal, conflict_strategy, scenes, code_plan
- each scene object keys: index, title, narration, visual_plan, estimated_seconds

Planning requirements:
1. Build image_understanding first.
2. Build teaching_goal second.
3. Build 3 to 5 medium-granularity storyboard scenes for quick generation. Long generation may later expand them into finer batches.
4. The total storyboard duration must be close to {target_duration_seconds} seconds and never below 300 seconds.
5. Distribute estimated_seconds across scenes so their sum is close to {target_duration_seconds} seconds.
6. Each scene needs narration text suitable for subtitles.
7. Build a code_plan before code.
8. All plan fields and narration must be Chinese.

Code requirements:
1. Follow every ManimCE hard rule from the system prompt.
2. The code must define `GeneratedTeachingScene(Scene)`.
3. The code must be self-contained and not need external assets.
4. The scene should use diagrams, arrows, timelines, relationship cards, maps, process panels, formula-like Text labels, local zoom/highlight, and color emphasis as appropriate to the storyboard.
5. If the topic is abstract or unclear, create a neutral relationship/process diagram from the current prompt. Do not default to axes, vectors, or projection unless the current storyboard is mathematical.
6. The actual rendered Manim video should be close to {target_duration_seconds} seconds. Use several short animations plus deliberate `self.wait(...)` pauses after each teaching beat. Do not finish in under 300 seconds.
7. On-screen labels and explanation Text must be Chinese and should use `font="Microsoft YaHei"`.

User prompt:
{user_prompt}

Image context:
{image_context}

Input priority rule:
{priority_rule}
"""

GENERATION_STRATEGY_PROMPT = """Design the generation strategy for a long teaching animation.

Output strict JSON only with keys:
- image_understanding
- teaching_goal
- conflict_strategy
- target_duration_seconds
- estimated_scene_count
- ai_call_count
- batches
- code_plan: must be a plain string. Do not return an object or array for code_plan.

Each batch object must contain:
- batch_index
- stage: 1, 2, or 3
- title
- goal
- scene_count
- duration_seconds

Rules:
1. Target duration is {target_duration_seconds} seconds and must never be below 300 seconds.
2. Do not solve long duration by stretching waits. Increase teaching detail.
3. Use fine-grained storyboard shots, around 15 to 25 seconds per shot.
4. Split the work into multiple AI storyboard calls. Use at least 3 batches and usually one batch per stage section.
5. Stage 1 should build context, prerequisites, definitions, and the concrete model.
6. Stage 2 should develop the main derivation/explanation with several visual steps.
7. Stage 3 should handle examples, mistakes, summary, and final stitching/export.
8. Each stage must contain multiple storyboard shots.
9. `code_plan` must be a concise plain string. If you need multiple items, write them as semicolon-separated text inside the string.
10. Return all text fields in Chinese.
11. `code_plan` must name the visual motif and the reusable layout style for this exact topic. It must not name old examples, previous topics, or generic vector/projection fallback visuals.

User prompt:
{user_prompt}

Image context:
{image_context}

Input priority rule:
{priority_rule}
"""

STORYBOARD_BATCH_PROMPT = """Generate one fine-grained storyboard batch for a long Manim teaching animation.

Output strict JSON only with key: scenes.
Each scene object keys: index, title, narration, visual_plan, estimated_seconds.

Batch:
{batch_json}

Global teaching goal:
{teaching_goal}

Existing scene titles to avoid repeating:
{existing_titles}

Rules:
1. Generate exactly {scene_count} scenes.
2. Scene indexes must start at {start_index}.
3. The batch duration should be close to {duration_seconds} seconds.
4. Each scene should add new teaching content, not just restate the same point.
5. Use lower-granularity/finer storyboard beats: one visual action or one teaching idea per scene.
6. Narration should be concrete enough for subtitles.
7. Visual plans must be implementation-ready: name concrete visible objects, approximate placement, enter/keep/exit behavior, and the intended transformation.
8. Scene titles, narration, and visual plans must be Chinese.
9. Do not use a generic coordinate plane or vector diagram unless this batch is explicitly about math, physics, force, functions, coordinates, or vectors.
"""

CODE_FROM_PLAN_PROMPT = """Generate runnable ManimCE code from this full long-form teaching plan.

Output strict JSON only with key: manim_code.

Teaching goal:
{teaching_goal}

Target duration:
{target_duration_seconds} seconds

Storyboard JSON:
{storyboard_json}

Code plan:
{code_plan}

Rules:
1. Follow every ManimCE hard rule from the system prompt.
2. Do not create a short video by skipping storyboard beats.
3. Do not create a long video only by adding huge `self.wait(...)` calls. Each storyboard scene must correspond to a visible teaching beat.
4. It is acceptable to use moderate waits for narration pacing, but each wait should follow a meaningful new visual state.
5. Use Text instead of MathTex.
6. Keep labels short and Chinese; use `font="Microsoft YaHei"` for Chinese `Text`.
7. The final code must define `GeneratedTeachingScene(Scene)`.
8. Keep the code conservative and linear: define each mobject before using it; never reference a variable inside its own assignment.
9. Do not use `self.camera.frame` because the required class is `Scene`, not `MovingCameraScene`.
10. For `VMobject`, create it first and then call setters separately; do not pass `color` or `stroke_width` into `set_points_smoothly`.
11. Treat the storyboard JSON as the primary source of truth. Do not reinterpret the topic and do not import visual ideas from examples.
12. Do not reuse examples or assets from previous topics. Every visible label, diagram, object, and scene must come from the current teaching goal and storyboard.
13. Do not use a generic visual shell such as `generic_board`, `core_region`, `idea_cards`, vague topic cards, or an abstract polygon with labels. Those are failure modes.
14. For every storyboard scene, implement the concrete nouns and actions in `visual_plan`. If it says rail/subgrade/ballast, draw rails, sleepers, ballast particles, cross-section layers, load arrows, drainage arrows, machinery, etc. If it says bridge, draw bridge components. If it says platform, draw platform UI objects. Do not replace them with unrelated cards.
15. Use simple symbolic diagrams derived from the storyboard only after extracting concrete objects: layered sections, component assemblies, arrows, particles, flows, comparisons, timelines, labels, and local highlights.
16. Use Axes/NumberPlane/vector/projection diagrams only when the storyboard explicitly asks for coordinates, graphing, vectors, functions, force diagrams, or equations.
17. Before returning code, mentally check each storyboard scene: active objects, enter objects, keep objects, exit objects, transform objects, and overlap/focus.
18. Do not add placeholder or meta end cards such as "segment demo complete", "visuals come from the current plan", "no old assets used", or similar self-referential text. The final frames must still teach the current topic.
19. Adjacent segments must not use the same base diagram unless the storyboard explicitly says to continue the same diagram. If two visual_plans differ, rebuild the visual composition for the current action instead of reusing the previous layout.
"""

SEGMENT_CODE_PROMPT = """Generate runnable ManimCE code for one segment of a larger course.

Output strict JSON only with key: manim_code.

Course teaching goal:
{teaching_goal}

Segment:
- index: {segment_index} of {segment_count}
- target duration: {segment_duration_seconds} seconds

Segment storyboard JSON:
{storyboard_json}

Course code plan:
{code_plan}

Rules:
1. Follow every ManimCE hard rule from the system prompt.
2. Generate only this segment, not the full course.
3. Make the segment visually dense: several small visible beats, short transitions, clear diagram state changes, and no long empty waits.
4. Keep code mostly linear and simple. Do not create complex helper functions unless they are trivial and fully defined before use.
5. Use Text instead of MathTex.
6. Keep labels short and Chinese; use `font="Microsoft YaHei"` for Chinese `Text`.
7. The final code must define `GeneratedTeachingScene(Scene)`.
8. The code must be self-contained because this segment is rendered independently before final stitching.
9. Define each mobject before using it; never reference a variable inside its own assignment.
10. Do not use `self.camera.frame` because the required class is `Scene`, not `MovingCameraScene`.
11. For `VMobject`, create it first and then call setters separately; do not pass `color` or `stroke_width` into `set_points_smoothly`.
12. Treat this segment storyboard as the primary source of truth. Do not reinterpret the topic and do not import visual ideas from examples.
13. Do not reuse examples or assets from previous topics. Every visible label, diagram, object, and scene must come from this segment storyboard.
14. Do not use a generic visual shell such as `generic_board`, `core_region`, `idea_cards`, vague topic cards, or an abstract polygon with labels. Those are failure modes.
15. For every storyboard scene, implement the concrete nouns and actions in `visual_plan`. If it says rail/subgrade/ballast, draw rails, sleepers, ballast particles, cross-section layers, load arrows, drainage arrows, machinery, etc. If it says bridge, draw bridge components. If it says platform, draw platform UI objects. Do not replace them with unrelated cards.
16. Use simple symbolic diagrams derived from the storyboard only after extracting concrete objects: layered sections, component assemblies, arrows, particles, flows, comparisons, timelines, labels, and local highlights.
17. Use Axes/NumberPlane/vector/projection diagrams only when the storyboard explicitly asks for coordinates, graphing, vectors, functions, force diagrams, or equations.
18. Before returning code, mentally check each storyboard scene: active objects, enter objects, keep objects, exit objects, transform objects, and overlap/focus.
19. Do not add placeholder or meta end cards such as "segment demo complete", "visuals come from the current plan", "no old assets used", or similar self-referential text. The final frames must still teach the current topic.
20. This segment must have a distinct visual action from adjacent segments. Avoid reusing the same rail/subgrade/ballast cross-section unless the current visual_plan explicitly requires that cross-section.
"""

REPAIR_PROMPT = """Repair this Manim Community Edition code.

Output strict JSON only with keys: repaired_code, notes.

Repair rules:
1. Do not change the teaching goal.
2. Follow every ManimCE hard rule from the system prompt.
3. Keep `GeneratedTeachingScene(Scene)`.
4. Remove fragile APIs, external assets, all MathTex/LaTeX when LaTeX errors appear, and speculative methods. Keep Chinese Text, preferably with `font="Microsoft YaHei"`.
5. If the error is about missing local packages such as `No module named manim`, say in notes that it is an environment issue and return a simple valid ManimCE scene.
6. If the error says visual consistency failed, remove stale-topic objects and rebuild the visual layer from the current teaching goal and each scene's visual_plan only. Do not keep generic_board/core_region/idea_cards, vague cards, or coordinate/vector/projection placeholders for non-math topics.

Teaching goal:
{teaching_goal}

Current code:
{code}

Render error:
{error_log}
"""
