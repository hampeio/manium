MANIMCE_CODE_RULES = """
ManimCE 代码硬性规则（依据本地 manimce-best-practices）：
1. 仅使用 Manim Community Edition，必须写 `from manim import *`，禁止使用 manimlib、InteractiveScene 或 ManimGL API。
2. 只定义一个可渲染类：`class GeneratedTeachingScene(Scene):`，并实现 `construct(self)`。
3. 在 JSON 字符串中返回原始 Python 源码，不要使用 Markdown 代码围栏。
4. 优先使用稳定对象：Scene、Text、VGroup、Group、Dot、Line、Arrow、DashedLine、Brace、Rectangle、Circle、Square、Polygon。
5. 仅当分镜明确需要坐标、函数、向量、图像或物理测量时，才使用 Axes 或 NumberPlane；禁止把坐标轴作为通用占位图。
6. 优先使用稳定动画：Create、Write、FadeIn、FadeOut、GrowArrow、Transform、ReplacementTransform、TransformFromCopy、Circumscribe、LaggedStart、Succession。
7. 使用 `self.play(...)` 和 `self.wait(...)`；单次 run_time 通常控制在 0.5 到 2 秒。
8. 使用 move_to、shift、next_to、to_edge、to_corner、arrange、arrange_in_grid 布局，不要按屏幕像素猜位置。
9. 线和箭头必须提供明确起点与终点；向量优先使用 `Vector([x, y, 0])` 或从 ORIGIN 出发的 Arrow。
10. 教学标题、旁白、字幕、画面标签和总结全部使用中文，变量或公式确需拉丁字符时除外。
11. 中文 `Text` 尽量指定 `font="Microsoft YaHei"`，标签保持简短，避免拥挤和重叠。
12. 默认不要使用 MathTex。第一版 Windows 环境可能没有 LaTeX，公式优先写成 `Text("A x = b", font_size=34)`。
13. 修复时若发现 LaTeX 错误，立即把 MathTex 替换为 Text。
14. 禁止使用 `axes.add_coordinates()`、`axis.add_numbers()`、DecimalNumber、Integer。
15. 坐标轴标签使用 Text 放置，禁止向 `get_x_axis_label` 或 `get_y_axis_label` 传字符串。
16. Manim 代码不得依赖外部图片、SVG、插件、网络、音频或 TTS；音频由应用在渲染后处理。
17. 每屏最多保留一个标题、一个主图、一个短公式和少量标签。
18. 使用深色背景，例如 `self.camera.background_color = "#111827"`。
19. 禁止猜测不确定 API；不确定时使用简单对象和简单变换。
20. 代码必须能通过 `python -m manim -qm scene.py GeneratedTeachingScene` 运行。
"""


SYSTEM_PROMPT = f"""你是一名资深教学动画导演和 Manim Community Edition 工程师。
必须先规划再写代码。整体视觉接近 3Blue1Brown：深色背景、清晰图解、彩色重点、流畅变换、少量文字。
除变量、公式和技术专名外，所有教学内容、说明和结果都必须使用中文。
只输出严格 JSON，不要输出 Markdown 或额外解释。

{MANIMCE_CODE_RULES}
"""


PLAN_AND_CODE_PROMPT = """根据输入生成教学动画规划和可运行的 ManimCE 代码。

仅输出严格 JSON，顶层字段为 plan、manim_code。
plan 必须包含：image_understanding、teaching_goal、conflict_strategy、scenes、code_plan。
每个 scenes 项必须包含：index、title、narration、visual_plan、estimated_seconds。

规划要求：
1. 先形成图像理解，再确定教学目标。
2. 快速生成默认拆成 3 到 5 个中颗粒度分镜；长视频后续可继续细分。
3. 分镜总时长应接近 {target_duration_seconds} 秒，且不得少于 300 秒。
4. estimated_seconds 总和应接近目标总时长。
5. 每段旁白必须可直接用于中文字幕和配音。
6. 生成代码前必须先形成 code_plan。
7. 所有规划字段与旁白使用中文。

代码要求：
1. 严格遵守系统提示词中的全部 ManimCE 规则。
2. 必须定义 `GeneratedTeachingScene(Scene)`，代码必须自包含。
3. 根据分镜选择图形、箭头、时间线、关系图、地图、流程图、公式文本、局部强调等表现方式。
4. 抽象主题应从当前提示词提取关系和流程，不得默认使用坐标轴、向量或投影图。
5. 视频时长应接近 {target_duration_seconds} 秒。通过增加有效教学动作实现时长，禁止仅拉长等待。
6. 画面文字使用中文，并优先使用 `font="Microsoft YaHei"`。

用户提示词：
{user_prompt}

图像内容：
{image_context}

输入优先级：
{priority_rule}
"""


GENERATION_STRATEGY_PROMPT = """为长教学动画设计生成策略。

仅输出严格 JSON，字段为：
image_understanding、teaching_goal、conflict_strategy、target_duration_seconds、
estimated_scene_count、ai_call_count、batches、code_plan。
code_plan 必须是普通字符串，禁止返回对象或数组。

每个 batches 项必须包含：
batch_index、stage（只能为 1、2、3）、title、goal、scene_count、duration_seconds。

规则：
1. 目标时长为 {target_duration_seconds} 秒，不得少于 300 秒。
2. 通过增加教学内容实现长时长，禁止只拉长等待。
3. 使用细颗粒度分镜，每段约 15 到 25 秒。
4. 至少拆成 3 个分镜批次，并合理安排模型调用次数。
5. 第一阶段负责背景、前置知识、定义和具体模型。
6. 第二阶段负责核心原理、推导和多步视觉解释。
7. 第三阶段负责例子、常见错误、总结和最终导出。
8. 每个阶段必须包含多个分镜。
9. code_plan 用分号分隔要点，必须描述当前主题独有的视觉母题和布局，禁止引用旧主题或通用占位图。
10. 所有文本字段必须使用中文。

用户提示词：
{user_prompt}

图像内容：
{image_context}

输入优先级：
{priority_rule}
"""


STORYBOARD_BATCH_PROMPT = """为长篇 Manim 教学动画生成一个细颗粒度分镜批次。

仅输出严格 JSON，顶层字段为 scenes。
每个分镜必须包含：index、title、narration、visual_plan、estimated_seconds。

当前批次：
{batch_json}

全局教学目标：
{teaching_goal}

已有标题（不得重复）：
{existing_titles}

规则：
1. 必须准确生成 {scene_count} 个分镜，编号从 {start_index} 开始。
2. 本批次总时长接近 {duration_seconds} 秒。
3. 每个分镜必须增加新的教学内容，不能换句话重复。
4. 每个分镜只承担一个视觉动作或一个教学要点。
5. 旁白应具体、自然，可直接用于字幕和中文配音。
6. visual_plan 必须可直接实现：写明可见对象、相对位置、进入、保留、退出和变换动作。
7. 标题、旁白和视觉计划全部使用中文。
8. 除非主题明确涉及数学、物理、受力、函数、坐标或向量，否则禁止使用通用坐标平面或向量图。
"""


CODE_FROM_PLAN_PROMPT = """根据完整长篇教学计划生成可运行的 ManimCE 代码。

仅输出严格 JSON，字段为 manim_code。

教学目标：
{teaching_goal}

目标时长：
{target_duration_seconds} 秒

分镜 JSON：
{storyboard_json}

代码计划：
{code_plan}

规则：
1. 严格遵守系统提示词中的全部 ManimCE 规则。
2. 不得跳过分镜来生成短视频，也不得只靠巨大 `self.wait(...)` 拉长视频。
3. 每个分镜必须对应新的可见教学状态；旁白停顿只能出现在有效画面变化之后。
4. 使用 Text 替代 MathTex；中文 Text 优先指定 Microsoft YaHei。
5. 必须定义 `GeneratedTeachingScene(Scene)`。
6. 代码保持保守、线性，所有对象必须先定义后使用，禁止在变量自身赋值中引用该变量。
7. 禁止使用 `self.camera.frame`，因为目标类是 Scene。
8. VMobject 应先创建再单独设置属性，不要向 set_points_smoothly 传 color 或 stroke_width。
9. 分镜 JSON 是唯一内容依据，不得重新解释主题或导入示例中的旧素材。
10. 禁止复用旧主题的标签、图形和对象。
11. 禁止 generic_board、core_region、idea_cards、模糊主题卡片和“多边形加标签”式通用占位画面。
12. 必须把 visual_plan 中的具体名词和动作画出来，不能替换成无关卡片。
13. 只有分镜明确要求时才能使用 Axes、NumberPlane、向量或投影图。
14. 返回前逐段检查对象的进入、保留、退出、变换、遮挡和焦点。
15. 禁止添加“分镜演示完成”“素材来自当前计划”等自述或占位结束画面。
16. 相邻分镜若未明确要求延续同一图，应使用不同的主图、空间布局或动画动作。
"""


SEGMENT_CODE_PROMPT = """为长课程中的一个独立片段生成可运行的 ManimCE 代码。

仅输出严格 JSON，字段为 manim_code。

课程教学目标：
{teaching_goal}

当前片段：第 {segment_index} 段，共 {segment_count} 段
目标时长：{segment_duration_seconds} 秒

当前片段分镜 JSON：
{storyboard_json}

课程代码计划：
{code_plan}

规则：
1. 严格遵守系统提示词中的全部 ManimCE 规则。
2. 只生成当前片段，不要生成整门课程。
3. 画面应有多个短而明确的视觉节拍、状态变化和过渡，禁止长时间空白等待。
4. 代码保持线性和简单；辅助函数必须简短且先定义后使用。
5. 使用 Text 替代 MathTex；中文 Text 优先指定 Microsoft YaHei。
6. 必须定义 `GeneratedTeachingScene(Scene)`，且代码必须自包含。
7. 禁止使用 `self.camera.frame`，禁止变量未定义和自引用。
8. 当前分镜是唯一内容依据，不得重新猜测主题或导入旧主题素材。
9. 禁止 generic_board、core_region、idea_cards、模糊卡片和抽象多边形占位图。
10. 必须把 visual_plan 中的具体对象、关系和动作绘制出来。
11. 只有当前分镜明确要求时才能使用坐标轴、向量、函数图或投影图。
12. 返回前检查对象进入、保留、退出、变换、遮挡和视觉焦点。
13. 禁止出现“分镜演示完成”“未使用旧素材”等元说明或占位画面。
14. 当前片段必须与相邻片段具有不同的主要视觉动作；除非 visual_plan 明确要求延续，否则不要复用同一底图。
"""


REPAIR_PROMPT = """修复下面的 Manim Community Edition 代码。

仅输出严格 JSON，字段为 repaired_code、notes。
notes 必须使用中文。

修复规则：
1. 不得改变教学目标和当前分镜内容。
2. 严格遵守系统提示词中的全部 ManimCE 规则。
3. 保留 `GeneratedTeachingScene(Scene)`。
4. 删除脆弱 API、外部素材和推测性方法；遇到 LaTeX 错误时把 MathTex 全部替换为 Text。
5. 中文 Text 优先指定 `font="Microsoft YaHei"`。
6. 如果错误来自本地环境缺少 manim 等软件包，在 notes 中明确说明环境问题，并返回最小可运行的 ManimCE 场景。
7. 如果错误来自视觉一致性检查，必须删除旧主题对象、通用卡片、非数学主题中的坐标或向量占位图，并严格按当前 visual_plan 重建画面。

教学目标与当前分镜：
{teaching_goal}

当前代码：
{code}

渲染或检查错误：
{error_log}
"""
