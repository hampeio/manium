import base64
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from backend.ai.model_config import ModelRequestConfig
from backend.ai.prompts import (
    CODE_FROM_PLAN_PROMPT,
    GENERATION_STRATEGY_PROMPT,
    PLAN_AND_CODE_PROMPT,
    REPAIR_PROMPT,
    SEGMENT_CODE_PROMPT,
    STORYBOARD_BATCH_PROMPT,
    SYSTEM_PROMPT,
)
from backend.ai.schemas import (
    CodeGenerationResult,
    GeneratedAnimation,
    GenerationStrategy,
    RepairResult,
    StoryboardBatchResult,
    StoryboardBatchSpec,
    StoryboardScene,
    TeachingPlan,
)

logger = logging.getLogger(__name__)

RECOVERABLE_MODEL_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
    httpx.RequestError,
    OSError,
    json.JSONDecodeError,
    ValidationError,
)


class ModelRouter:
    """Routes generation requests to OpenAI-compatible providers or a local mock."""

    def __init__(self, config: ModelRequestConfig, trace_dir: Path | None = None):
        self.config = config
        self.trace_dir = trace_dir
        self._trace_index = 0

    async def plan_generation_strategy(
        self,
        user_prompt: str,
        image_path: Path | None,
        image_context: str,
        priority_rule: str,
        total_duration_seconds: int,
    ) -> GenerationStrategy:
        """First AI call: produce the outline, duration allocation, and follow-up call count."""

        if self.config.provider == "mock" or not self.config.api_key:
            return self._mock_strategy(user_prompt, image_context, priority_rule, total_duration_seconds)

        prompt = GENERATION_STRATEGY_PROMPT.format(
            user_prompt=user_prompt or "(empty)",
            image_context=image_context or "(none)",
            priority_rule=priority_rule,
            target_duration_seconds=total_duration_seconds,
        )
        try:
            data = await self._chat_json("outline_strategy", prompt, image_path)
            parsed = GenerationStrategy.model_validate_json(data["choices"][0]["message"]["content"])
            self._write_trace_parsed(data["_trace_id"], "outline_strategy", parsed.model_dump())
            return parsed
        except RECOVERABLE_MODEL_ERRORS as exc:
            self._write_fallback_trace(
                "outline_strategy_fallback",
                exc,
                "Outline strategy call failed. Falling back to local strategy generation.",
            )
            return self._mock_strategy(user_prompt, image_context, priority_rule, total_duration_seconds)

    async def generate_storyboard_batch(
        self,
        strategy: GenerationStrategy,
        batch: StoryboardBatchSpec,
        start_index: int,
        existing_titles: list[str],
    ) -> StoryboardBatchResult:
        """Follow-up AI call: expand one outline batch into fine-grained storyboard shots."""

        if self.config.provider == "mock" or not self.config.api_key:
            return self._mock_storyboard_batch(strategy, batch, start_index)

        prompt = STORYBOARD_BATCH_PROMPT.format(
            batch_json=json.dumps(batch.model_dump(), ensure_ascii=False, indent=2),
            teaching_goal=strategy.teaching_goal,
            existing_titles=", ".join(existing_titles[-30:]) or "(none)",
            scene_count=batch.scene_count,
            start_index=start_index,
            duration_seconds=batch.duration_seconds,
        )
        try:
            data = await self._chat_json(f"storyboard_batch_{batch.batch_index}", prompt, None)
            parsed = StoryboardBatchResult.model_validate_json(data["choices"][0]["message"]["content"])
            self._write_trace_parsed(data["_trace_id"], f"storyboard_batch_{batch.batch_index}", parsed.model_dump())
            if self._is_low_information_storyboard(parsed, strategy, batch):
                self._write_fallback_trace(
                    f"storyboard_batch_{batch.batch_index}_quality_fallback",
                    ValueError("Storyboard batch is too generic for the current topic."),
                    "Storyboard batch returned low-information generic shots. Replacing with topic-grounded local storyboard.",
                )
                return self._mock_storyboard_batch(strategy, batch, start_index)
            return parsed
        except RECOVERABLE_MODEL_ERRORS as exc:
            self._write_fallback_trace(
                f"storyboard_batch_{batch.batch_index}_fallback",
                exc,
                "Storyboard batch call failed. Falling back to local storyboard expansion for this batch.",
            )
            return self._mock_storyboard_batch(strategy, batch, start_index)

    def _is_low_information_storyboard(self, result: StoryboardBatchResult, strategy: GenerationStrategy, batch: StoryboardBatchSpec) -> bool:
        topic_text = f"{strategy.teaching_goal} {batch.goal}".lower()
        math_like_topic = any(term in topic_text for term in ["数学", "函数", "向量", "矩阵", "坐标", "公式", "物理", "受力", "force", "math", "vector"])
        generic_terms = [
            "提出问题",
            "定义对象",
            "建立直觉",
            "单步变换",
            "公式连接",
            "显示紧凑标题",
            "显示坐标",
            "高亮目标",
            "短公式文本",
            "几何元素",
            "coordinate",
            "formula",
        ]
        hits = 0
        too_short_visuals = 0
        for scene in result.scenes:
            scene_text = f"{scene.title} {scene.narration} {scene.visual_plan}".lower()
            if any(term.lower() in scene_text for term in generic_terms):
                hits += 1
            if len(scene.visual_plan.strip()) < 36:
                too_short_visuals += 1
            if not math_like_topic and any(term in scene_text for term in ["坐标", "公式", "几何元素", "coordinate", "axis", "vector"]):
                hits += 2
        return hits >= max(2, len(result.scenes) // 2) or too_short_visuals > len(result.scenes) // 2

    async def generate_code_from_plan(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Final AI call: generate Manim code from the fully expanded storyboard."""

        if self.config.provider == "mock" or not self.config.api_key:
            return self._code_from_storyboard(plan, total_duration_seconds)

        prompt = CODE_FROM_PLAN_PROMPT.format(
            teaching_goal=plan.teaching_goal,
            target_duration_seconds=total_duration_seconds,
            storyboard_json=json.dumps([scene.model_dump() for scene in plan.scenes], ensure_ascii=False, indent=2),
            code_plan=plan.code_plan,
        )
        try:
            data = await self._chat_json("code_from_full_plan", prompt, None, max_tokens=8192)
            parsed = CodeGenerationResult.model_validate_json(data["choices"][0]["message"]["content"])
            self._write_trace_parsed(data["_trace_id"], "code_from_full_plan", parsed.model_dump())
            return parsed.manim_code
        except RECOVERABLE_MODEL_ERRORS as exc:
            self._write_fallback_trace(
                "code_from_full_plan_fallback",
                exc,
                "Model code generation failed after the full storyboard was ready. Falling back to local Manim code synthesis.",
            )
            return self._code_from_storyboard(plan, total_duration_seconds)

    async def generate_code_for_segment(
        self,
        plan: TeachingPlan,
        *,
        segment_index: int,
        segment_count: int,
        segment_duration_seconds: int,
    ) -> str:
        """Generate one independently renderable Manim scene for a course segment."""

        if self.config.provider == "mock" or not self.config.api_key:
            return self._code_from_storyboard(plan, segment_duration_seconds)

        prompt = SEGMENT_CODE_PROMPT.format(
            teaching_goal=plan.teaching_goal,
            segment_index=segment_index,
            segment_count=segment_count,
            segment_duration_seconds=segment_duration_seconds,
            storyboard_json=json.dumps([scene.model_dump() for scene in plan.scenes], ensure_ascii=False, indent=2),
            code_plan=plan.code_plan,
        )
        try:
            data = await self._chat_json(f"segment_{segment_index:02d}_code", prompt, None, max_tokens=8192)
            parsed = CodeGenerationResult.model_validate_json(data["choices"][0]["message"]["content"])
            self._write_trace_parsed(data["_trace_id"], f"segment_{segment_index:02d}_code", parsed.model_dump())
            return parsed.manim_code
        except RECOVERABLE_MODEL_ERRORS as exc:
            self._write_fallback_trace(
                f"segment_{segment_index:02d}_code_fallback",
                exc,
                "Segment code generation failed. Falling back to local Manim code synthesis for this segment.",
            )
            return self._code_from_storyboard(plan, segment_duration_seconds)

    async def generate_animation(
        self,
        user_prompt: str,
        image_path: Path | None,
        image_context: str,
        priority_rule: str,
        total_duration_seconds: int = 300,
    ) -> GeneratedAnimation:
        if self.config.provider == "mock" or not self.config.api_key:
            return self._mock_animation(user_prompt, image_context, priority_rule, total_duration_seconds)

        prompt = PLAN_AND_CODE_PROMPT.format(
            user_prompt=user_prompt or "(empty)",
            image_context=image_context or "(none)",
            priority_rule=priority_rule,
            target_duration_seconds=total_duration_seconds,
        )
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_content(prompt, image_path)},
            ],
            "temperature": 0.25,
            "response_format": {"type": "json_object"},
        }
        trace_id = self._write_trace_request("generate", payload)
        data = await self._post_chat(payload)
        self._write_trace_response(trace_id, "generate", data)
        content = data["choices"][0]["message"]["content"]
        parsed = GeneratedAnimation.model_validate(json.loads(content))
        self._write_trace_parsed(trace_id, "generate", parsed.model_dump())
        return parsed

    async def _chat_json(self, step: str, prompt: str, image_path: Path | None, max_tokens: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_content(prompt, image_path)},
            ],
            "temperature": 0.25,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        trace_id = self._write_trace_request(step, payload)
        data = await self._post_chat(payload)
        self._write_trace_response(trace_id, step, data)
        data["_trace_id"] = trace_id
        return data

    async def repair_code(self, teaching_goal: str, code: str, error_log: str) -> RepairResult:
        if self.config.provider == "mock" or not self.config.api_key:
            return RepairResult(repaired_code=self._fallback_code(teaching_goal, 300), notes="Local mock repair generated a conservative runnable scene.")

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": REPAIR_PROMPT.format(teaching_goal=teaching_goal, code=code, error_log=error_log[-6000:])},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        trace_id = self._write_trace_request("repair", payload)
        try:
            data = await self._post_chat(payload)
            self._write_trace_response(trace_id, "repair", data)
            content = data["choices"][0]["message"]["content"]
            parsed = RepairResult.model_validate(json.loads(content))
            self._write_trace_parsed(trace_id, "repair", parsed.model_dump())
            return parsed
        except RECOVERABLE_MODEL_ERRORS as exc:
            self._write_fallback_trace(
                "repair_fallback",
                exc,
                "Repair call failed. Falling back to a conservative runnable local Manim scene.",
            )
            return RepairResult(repaired_code=self._fallback_code(teaching_goal, 300), notes=f"模型修复调用失败，已使用本地可运行兜底版本：{exc}")

    async def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        timeout = httpx.Timeout(connect=20, read=180, write=30, pool=20)
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, 4):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as exc:
                    body = exc.response.text[:800]
                    raise RuntimeError(
                        f"Model provider returned HTTP {exc.response.status_code} {exc.response.reason_phrase}. "
                        f"Check API balance, model access, Base URL, and model name. Response: {body}"
                    ) from exc
                except (httpx.RemoteProtocolError, httpx.ReadError, httpx.TimeoutException, httpx.ConnectError) as exc:
                    last_error = exc
                    if attempt == 3:
                        break
                    await asyncio.sleep(1.5 * attempt)
        assert last_error is not None
        raise last_error

    def _build_user_content(self, prompt: str, image_path: Path | None) -> str | list[dict[str, Any]]:
        if not image_path:
            return prompt
        try:
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            return [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
            ]
        except OSError:
            logger.warning("Image could not be attached to model request; continuing with text context.")
            return prompt

    def _write_trace_request(self, step: str, payload: dict[str, Any]) -> str:
        trace_id = self._next_trace_id(step)
        self._write_trace_file(trace_id, "request", self._sanitize_trace_payload(payload))
        return trace_id

    def _write_trace_response(self, trace_id: str, step: str, response: dict[str, Any]) -> None:
        self._write_trace_file(trace_id, "response", self._sanitize_trace_payload(response))

    def _write_trace_parsed(self, trace_id: str, step: str, parsed: dict[str, Any]) -> None:
        self._write_trace_file(trace_id, "parsed", parsed)

    def _write_fallback_trace(self, step: str, exc: Exception, strategy: str) -> None:
        self._write_trace_file(
            self._next_trace_id(step),
            "fallback",
            {
                "error_type": type(exc).__name__,
                "reason": str(exc),
                "strategy": strategy,
            },
        )

    def _next_trace_id(self, step: str) -> str:
        self._trace_index += 1
        return f"{self._trace_index:03d}_{step}"

    def _write_trace_file(self, trace_id: str, kind: str, data: object) -> None:
        if not self.trace_dir:
            return
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        path = self.trace_dir / f"{trace_id}_{kind}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _sanitize_trace_payload(self, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized = {}
            for key, item in value.items():
                if key.lower() in {"authorization", "api_key"}:
                    sanitized[key] = "[REDACTED]"
                elif key == "image_url":
                    sanitized[key] = {"url": "[base64 image omitted]"}
                else:
                    sanitized[key] = self._sanitize_trace_payload(item)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize_trace_payload(item) for item in value]
        if isinstance(value, str) and value.startswith("data:image/"):
            return "[base64 image omitted]"
        return value

    def _mock_animation(self, user_prompt: str, image_context: str, priority_rule: str, total_duration_seconds: int = 300) -> GeneratedAnimation:
        topic = user_prompt.strip() or image_context or "向量投影"
        base = max(300, int(total_duration_seconds)) // 9
        remainder = max(300, int(total_duration_seconds)) - base * 9
        scenes = [
            StoryboardScene(index=1, title="提出问题", narration=f"这一段先聚焦主题：{topic}。", visual_plan="显示标题和核心问题。", estimated_seconds=base + (1 if remainder > 0 else 0)),
            StoryboardScene(index=2, title="识别对象", narration="先把画面中需要解释的对象逐一命名。", visual_plan="出现坐标、结构或关键图形，并加上中文标签。", estimated_seconds=base + (1 if remainder > 1 else 0)),
            StoryboardScene(index=3, title="建立模型", narration="把真实问题转换成可以动画表达的简洁模型。", visual_plan="用线、箭头、颜色和局部强调锁定模型。", estimated_seconds=base + (1 if remainder > 2 else 0)),
            StoryboardScene(index=4, title="确定目标", narration="明确我们接下来要追踪的方向、力或变量。", visual_plan="高亮目标线段、方向或作用路径。", estimated_seconds=base + (1 if remainder > 3 else 0)),
            StoryboardScene(index=5, title="辅助关系", narration="借助辅助线或局部放大，看清隐藏关系。", visual_plan="显示虚线、投影点或局部结构。", estimated_seconds=base + (1 if remainder > 4 else 0)),
            StoryboardScene(index=6, title="公式连接", narration="把图形关系翻译成一条简洁的公式化表达。", visual_plan="在图旁显示短公式文本并配合颜色。", estimated_seconds=base + (1 if remainder > 5 else 0)),
            StoryboardScene(index=7, title="解释结果", narration="解释得到的量在原问题中代表什么。", visual_plan="让结果部分发光，同时弱化背景。", estimated_seconds=base + (1 if remainder > 6 else 0)),
            StoryboardScene(index=8, title="常见误区", narration="对比一个容易混淆的理解，并给出纠正。", visual_plan="用红色提示错误，再切换到正确关系。", estimated_seconds=base + (1 if remainder > 7 else 0)),
            StoryboardScene(index=9, title="总结结论", narration="最后收束成一句可以复用的结论。", visual_plan="显示总结框和关键关系。", estimated_seconds=base),
        ]
        plan = TeachingPlan(
            image_understanding=image_context or "未上传图片，本次根据提示词生成教学动画。",
            teaching_goal=f"用清晰的 Manim 教学动画解释：{topic}。",
            conflict_strategy=priority_rule,
            scenes=scenes,
            code_plan="使用中文 Text、图形、箭头、虚线、颜色强调和局部变换；避免只堆文字。",
        )
        return GeneratedAnimation(plan=plan, manim_code=self._fallback_code(plan.teaching_goal, total_duration_seconds))

    def _mock_strategy(self, user_prompt: str, image_context: str, priority_rule: str, total_duration_seconds: int) -> GenerationStrategy:
        topic = user_prompt.strip() or image_context or "向量投影"
        target = max(300, int(total_duration_seconds))
        scene_count = max(15, min(36, round(target / 20)))
        batch_count = max(3, min(9, round(scene_count / 5)))
        base_scenes = scene_count // batch_count
        scene_remainder = scene_count - base_scenes * batch_count
        base_duration = target // batch_count
        duration_remainder = target - base_duration * batch_count
        batches = []
        for index in range(batch_count):
            stage = min(3, int(index * 3 / batch_count) + 1)
            batches.append(
                StoryboardBatchSpec(
                    batch_index=index + 1,
                    stage=stage,
                    title=f"第 {stage} 阶段批次 {index + 1}",
                    goal=f"围绕“{topic}”补充分阶段的新视觉细节。",
                    scene_count=base_scenes + (1 if index < scene_remainder else 0),
                    duration_seconds=base_duration + (1 if index < duration_remainder else 0),
                )
            )
        return GenerationStrategy(
            image_understanding=image_context or "未上传图片，本次根据提示词生成教学动画。",
            teaching_goal=f"用足够细节解释“{topic}”，形成约 {target} 秒的中文教学动画。",
            conflict_strategy=priority_rule,
            target_duration_seconds=target,
            estimated_scene_count=scene_count,
            ai_call_count=1 + batch_count + 1,
            batches=batches,
            code_plan="使用细颗粒度图解状态；每个分镜都加入新的可见教学信息；不要靠长等待凑时长。",
        )

    def _mock_storyboard_batch(self, strategy: GenerationStrategy, batch: StoryboardBatchSpec, start_index: int) -> StoryboardBatchResult:
        base = batch.duration_seconds // batch.scene_count
        remainder = batch.duration_seconds - base * batch.scene_count
        scene_templates = self._local_storyboard_templates(strategy, batch)
        scenes = []
        for offset in range(batch.scene_count):
            template = scene_templates[(start_index + offset - 1) % len(scene_templates)]
            seconds = base + (1 if offset < remainder else 0)
            scenes.append(
                StoryboardScene(
                    index=start_index + offset,
                    title=f"{batch.title}: {template[0]}",
                    narration=template[1],
                    visual_plan=template[2],
                    estimated_seconds=float(seconds),
                )
            )
        return StoryboardBatchResult(scenes=scenes)

        # Legacy generic templates below are intentionally unreachable. They are kept only to
        # minimize churn in older fallback code and will be removed in a later cleanup.
        scene_templates = [
            ("提出问题", "介绍这一小节要回答的精确问题。", "显示紧凑标题和高亮目标。"),
            ("定义对象", "先命名关键对象，再开始移动或推导。", "显示坐标、结构、标签和参考线。"),
            ("建立直觉", "把图形变化和背后的概念连接起来。", "动画显示辅助线、颜色强调和简短说明。"),
            ("单步变换", "只做一个小变换，并说明它为什么成立。", "移动或复制一个几何元素，同时保留淡化背景。"),
            ("公式连接", "把当前视觉步骤翻译成公式化文本。", "在高亮图形旁放置短公式文本。"),
            ("检查含义", "解释变换后的对象在原问题中的意义。", "用颜色对比原对象和派生对象。"),
            ("常见误区", "指出一个可能误解，并立刻纠正。", "先显示红色提示，再替换为正确关系。"),
            ("小结", "用一句可复用结论收束本节。", "把主要元素整理成总结布局。"),
        ]
        scenes = []
        for offset in range(batch.scene_count):
            template = scene_templates[(start_index + offset - 1) % len(scene_templates)]
            seconds = base + (1 if offset < remainder else 0)
            scenes.append(
                StoryboardScene(
                    index=start_index + offset,
                    title=f"{batch.title}: {template[0]}",
                    narration=template[1],
                    visual_plan=template[2],
                    estimated_seconds=float(seconds),
                )
            )
        return StoryboardBatchResult(scenes=scenes)

    def _local_storyboard_templates(self, strategy: GenerationStrategy, batch: StoryboardBatchSpec) -> list[tuple[str, str, str]]:
        topic = self._extract_topic_label(f"{strategy.teaching_goal} {batch.goal}") or "当前主题"
        text = f"{strategy.teaching_goal} {batch.goal}".lower()
        if any(term in text for term in ["扣件", "轨道", "钢轨", "弹条", "rail", "fastener"]):
            return [
                ("扣件系统整体视图", "先从侧视剖面看清钢轨、轨枕、垫板、弹条和螺栓的相对位置。", "画面中央绘制棕色轨枕和灰色钢轨断面，依次淡入垫板、轨距挡板、弹条、螺栓；每个部件用短中文标签和箭头指向，底部保留部件图例。"),
                ("弹条如何压住钢轨", "弹条通过弯曲变形持续给钢轨脚部施加扣压力。", "放大钢轨脚部和红色弹条，弹条由松弛曲线变为压紧曲线；向下粗箭头标注扣压力，接触点用黄色圆环闪烁。"),
                ("螺栓把旋转变成夹紧力", "螺母旋转下移，带动弹条压紧，形成稳定的夹紧力。", "右侧绘制螺栓杆和六角螺母，螺母 Rotate 并逐步下移；旁边出现旋转箭头和向下轴向力箭头，文字标注旋转到夹紧。"),
                ("力的传递路径", "夹紧力从螺栓传给弹条，再传给轨底，最后传到轨枕。", "用三段彩色箭头从螺栓头指向弹条、轨底、轨枕；每段箭头依次点亮，背景部件半透明，突出力流路径。"),
                ("列车荷载下的缓冲", "列车通过时钢轨振动，弹性扣件通过微小变形吸收冲击。", "上方车轮缓慢压过钢轨，钢轨出现轻微上下振动；红色弹条同步压缩回弹，旁边显示吸收振动的小波纹图标。"),
                ("安装顺序拆解", "扣件安装需要按顺序放置垫板、钢轨、挡板、弹条并拧紧螺母。", "从空白轨枕开始，数字 1 到 5 依次出现；每一步对应一个部件滑入或旋入，最后合成为完整扣件剖面。"),
                ("不同扣件类型对比", "不同扣件在弹条形状、扣压力和调整能力上不同。", "横向摆放三张对比卡片，分别画弧形、弯折形、环形弹条轮廓；下方用短标签写适用线路和调整能力。"),
                ("维护检查重点", "检查扣件时要关注螺栓松动、弹条疲劳、垫板磨耗和轨距变化。", "完整扣件图上依次出现四个检查标记，红色圈出松动螺栓和磨耗垫板，绿色勾标出正常状态。"),
            ]
        return [
            (f"{topic}的核心对象", f"先把{topic}中真正要解释的对象具体画出来。", f"左侧绘制{topic}的主对象示意图，右侧列出 3 个关键词卡片；关键词必须来自当前提示词和分镜目标。"),
            (f"{topic}的组成关系", f"把{topic}拆成几个可见部分，并说明它们如何连接。", "用部件卡片和箭头组成关系图，按从左到右的顺序逐个出现；每个部件只保留短中文标签。"),
            (f"{topic}的工作过程", f"用连续动作展示{topic}从输入到结果的过程。", "底部放阶段时间线，主画面中一个高亮点沿流程箭头移动；每到一站，相关部件变亮，其余对象半透明。"),
            (f"{topic}的关键变化", f"突出一个最重要的变化，说明变化前后差异。", "左右对比两个状态卡片，中间用 Transform 箭头连接；变化区域用黄色描边和放大圆圈强调。"),
            (f"{topic}的常见误解", f"指出理解{topic}时容易混淆的地方，并给出正确关系。", "先显示红色错误卡片并打叉，再替换为绿色正确卡片；主图中对应对象同步从红色变为绿色。"),
            (f"{topic}的小结", f"把{topic}收束成可复用的结构化结论。", "把主图缩小到左侧，右侧出现三行总结：对象、关系、结果；底部时间线全部点亮。"),
        ]

    def _extract_topic_label(self, text: str) -> str:
        quoted = re.findall(r"[“\"']([^“”\"']{2,18})[”\"']", text)
        if quoted:
            return quoted[0].strip()
        matches = re.findall(r"[\u4e00-\u9fffA-Za-z0-9\-]{2,16}", text)
        skip = {"Manim", "中文教学动画", "足够细节解释", "形成约", "围绕", "补充", "阶段", "视觉细节"}
        for item in matches:
            if item not in skip and not item.isdigit():
                return item
        return ""

    def _topic_text(self, plan: TeachingPlan, scene_limit: int | None = None) -> str:
        scenes = plan.scenes if scene_limit is None else plan.scenes[:scene_limit]
        return " ".join(
            [plan.teaching_goal, plan.code_plan]
            + [scene.title + " " + scene.narration + " " + scene.visual_plan for scene in scenes]
        ).lower()

    def _is_city_topic(self, plan: TeachingPlan) -> bool:
        topic_text = self._topic_text(plan)
        primary_city_keywords = [
            "city",
            "tourism",
            "tourist",
            "travel",
            "landmark",
            "scenic",
            "urban",
            "location",
            "geography",
            "shenyang",
            "liaoning",
            "\u57ce\u5e02",
            "\u5730\u7406",
            "\u5730\u7406\u4f4d\u7f6e",
            "\u6587\u65c5",
            "\u65c5\u6e38",
            "\u666f\u70b9",
            "\u6545\u5bab",
            "\u7701\u4f1a",
            "\u5730\u6807",
            "\u4ea4\u901a\u67a2\u7ebd",
            "\u6c88\u9633",
            "\u8fbd\u5b81",
        ]
        supporting_keywords = [
            "history",
            "culture",
            "industry",
            "\u5386\u53f2",
            "\u6587\u5316",
            "\u5de5\u4e1a",
        ]
        has_primary = any(keyword in topic_text for keyword in primary_city_keywords)
        has_supporting_context = sum(1 for keyword in supporting_keywords if keyword in topic_text) >= 2
        return has_primary or ("\u4ecb\u7ecd" in topic_text and has_supporting_context)

    def _is_country_topic(self, plan: TeachingPlan) -> bool:
        topic_text = self._topic_text(plan)
        country_keywords = [
            "china",
            "country",
            "nation",
            "national",
            "beijing",
            "great wall",
            "\u4e2d\u56fd",
            "\u4e2d\u534e",
            "\u56fd\u5bb6",
            "\u56fd\u65d7",
            "\u9996\u90fd",
            "\u5317\u4eac",
            "\u957f\u57ce",
            "\u4e1d\u7ef8\u4e4b\u8def",
            "\u56db\u5927\u53d1\u660e",
            "\u9ad8\u94c1",
        ]
        return any(keyword in topic_text for keyword in country_keywords)

    def _visual_terms_from_plan(self, plan: TeachingPlan, limit: int = 6) -> list[str]:
        """Extracts short visible labels from the current plan without using fixed topic templates."""

        candidates: list[str] = []
        for value in [plan.teaching_goal, plan.code_plan] + [scene.title for scene in plan.scenes] + [scene.visual_plan for scene in plan.scenes[:6]]:
            candidates.extend(re.findall(r"[\u4e00-\u9fff]{2,8}", value))
            for raw_part in (
                value.replace("，", ",")
                .replace("。", ",")
                .replace("、", ",")
                .replace("；", ",")
                .replace(":", ",")
                .replace("：", ",")
                .split(",")
            ):
                part = raw_part.strip().strip("“”\"' ")
                if 2 <= len(part) <= 8 and not any(skip in part.lower() for skip in ["manim", "text", "json", "self.wait"]):
                    candidates.append(part)
        deduped: list[str] = []
        for item in candidates:
            if item not in deduped:
                deduped.append(item)
            if len(deduped) >= limit:
                break
        while len(deduped) < limit:
            deduped.append(["主题对象", "关键背景", "主要关系", "发展脉络", "典型例子", "总结结论"][len(deduped)])
        return deduped

    def _labels_from_scene(self, scene: StoryboardScene, limit: int = 4) -> list[str]:
        """Extracts short labels for one storyboard beat, preserving the current topic."""

        text = f"{scene.title} {scene.narration} {scene.visual_plan}"
        candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9\-]{2,10}", text)
        stop_words = {
            "显示",
            "使用",
            "出现",
            "一个",
            "多个",
            "动画",
            "文字",
            "标注",
            "表示",
            "进行",
            "当前",
            "分镜",
            "介绍",
            "说明",
            "生成",
            "Text",
            "VGroup",
            "Rectangle",
            "Arrow",
        }
        labels: list[str] = []
        for item in candidates:
            item = item.strip("：:，,。.；;（）()")
            if len(item) < 2 or item in stop_words:
                continue
            if item not in labels:
                labels.append(item)
            if len(labels) >= limit:
                break
        fallback = ["对象", "结构", "作用", "结论"]
        while len(labels) < limit:
            labels.append(fallback[len(labels)])
        return labels

    def _generic_code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Compile storyboard visual plans into concrete Manim primitives.

        This is intentionally not a topic template.  It reads each scene's
        visual_plan and chooses small reusable visual skills: layered sections,
        force paths, water paths, particles, machinery, comparison diagrams,
        timelines, and relationship flows.
        """

        compact_timing = "COMPACT_TIMING" in plan.code_plan or "compact timing" in plan.code_plan.lower()
        safe_goal = plan.teaching_goal.replace("\\", "\\\\")[:110]
        lines = [
            "from manim import *",
            "import numpy as np",
            "",
            "",
            "def cn(text, font_size=24, color=WHITE):",
            "    return Text(text, font=\"Microsoft YaHei\", font_size=font_size, color=color)",
            "",
            "",
            "class GeneratedTeachingScene(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = \"#111827\"",
            f"        title = cn({json.dumps(safe_goal, ensure_ascii=True)}, font_size=28, color=WHITE).to_edge(UP)",
            "        subtitle = cn(\"分镜驱动生成：每一段都按 visual_plan 重新构图\", font_size=18, color=GRAY_A).next_to(title, DOWN, buff=0.12)",
            "        self.play(Write(title), FadeIn(subtitle, shift=DOWN * 0.12), run_time=1.2)",
            "        timeline = Line(LEFT * 4.5, RIGHT * 4.5, color=GRAY_B).shift(DOWN * 2.35)",
            "        scene_dots = VGroup()",
            f"        dot_count = {max(1, len(plan.scenes))}",
            "        for i in range(dot_count):",
            "            x = -4.2 + (8.4 * i / max(1, dot_count - 1))",
            "            scene_dots.add(Dot(np.array([x, -2.35, 0]), radius=0.055, color=GRAY_B))",
            "        timeline_group = VGroup(timeline, scene_dots)",
            "        self.play(Create(timeline), FadeIn(scene_dots), run_time=0.8)",
            "        active = VGroup()",
            "",
            "        def clear_active():",
            "            nonlocal active",
            "            if len(active) > 0:",
            "                self.play(FadeOut(active), run_time=0.35)",
            "            active = VGroup()",
            "",
            "        def layered_section():",
            "            subgrade = Rectangle(width=7.8, height=0.62, color=MAROON_B, fill_color='#6b4f35', fill_opacity=0.55).shift(DOWN * 1.25)",
            "            ballast = Polygon(LEFT * 3.15 + DOWN * 0.9, RIGHT * 3.15 + DOWN * 0.9, RIGHT * 2.35 + UP * 0.35, LEFT * 2.35 + UP * 0.35, color=ORANGE, fill_color='#7a5a22', fill_opacity=0.78)",
            "            sleepers = VGroup(*[Rectangle(width=0.34, height=2.25, color=GRAY_B, fill_color=GRAY_D, fill_opacity=0.75).rotate(PI/2).shift(RIGHT * x + UP * 0.42) for x in [-2.1, -1.25, -0.4, 0.45, 1.3, 2.15]])",
            "            rails = VGroup(Line(LEFT * 3.0 + UP * 0.92, RIGHT * 3.0 + UP * 0.92, color=GRAY_A, stroke_width=8), Line(LEFT * 3.0 + UP * 1.18, RIGHT * 3.0 + UP * 1.18, color=GRAY_A, stroke_width=8))",
            "            labels = VGroup(cn('钢轨', 20, GRAY_A).next_to(rails, UP, buff=0.08), cn('轨枕', 20, GRAY_B).move_to(LEFT * 3.55 + UP * 0.45), cn('道床 / 道砟', 20, ORANGE).move_to(LEFT * 3.65 + DOWN * 0.25), cn('路基', 20, MAROON_A).move_to(LEFT * 3.75 + DOWN * 1.25))",
            "            return VGroup(subgrade, ballast, sleepers, rails, labels)",
            "",
            "        def ballast_particles():",
            "            dots = VGroup()",
            "            for row, y in enumerate(np.linspace(-0.72, 0.15, 5)):",
            "                span = 2.8 - row * 0.22",
            "                for col, x in enumerate(np.linspace(-span, span, 9)):",
            "                    dots.add(RegularPolygon(n=5, radius=0.075, color=YELLOW_E, fill_color='#8a6b2c', fill_opacity=0.8).rotate((row + col) * 0.37).shift(RIGHT * x + UP * y))",
            "            return dots",
            "",
            "        def force_path():",
            "            top = UP * 1.65",
            "            arrows = VGroup(Arrow(top, UP * 0.9, color=RED_C, stroke_width=6, buff=0), Arrow(UP * 0.62, LEFT * 1.7 + DOWN * 0.55, color=YELLOW, stroke_width=4, buff=0), Arrow(UP * 0.62, RIGHT * 1.7 + DOWN * 0.55, color=YELLOW, stroke_width=4, buff=0), Arrow(UP * 0.25, DOWN * 1.05, color=ORANGE, stroke_width=5, buff=0))",
            "            return VGroup(arrows, cn('轮载', 20, RED_C).next_to(arrows[0], UP, buff=0.05), cn('扩散到更大面积', 20, YELLOW).shift(RIGHT * 2.4 + DOWN * 0.15))",
            "",
            "        def drainage_path():",
            "            drops = VGroup(*[Dot(LEFT * x + UP * 1.65, radius=0.045, color=BLUE_C) for x in [-1.8, -0.9, 0, 0.9, 1.8]])",
            "            flows = VGroup(Arrow(UP * 0.45, LEFT * 2.2 + DOWN * 0.65, color=BLUE_C, buff=0, stroke_width=4), Arrow(UP * 0.45, RIGHT * 2.2 + DOWN * 0.65, color=BLUE_C, buff=0, stroke_width=4))",
            "            return VGroup(drops, flows, cn('空隙排水', 21, BLUE_C).shift(RIGHT * 2.9 + UP * 0.45))",
            "",
            "        def elastic_spring():",
            "            points = [LEFT * 1.0 + DOWN * 1.35, LEFT * 0.65 + DOWN * 1.0, LEFT * 0.3 + DOWN * 1.35, RIGHT * 0.05 + DOWN * 1.0, RIGHT * 0.4 + DOWN * 1.35, RIGHT * 0.75 + DOWN * 1.0, RIGHT * 1.1 + DOWN * 1.35]",
            "            spring = VMobject(color=GREEN_B, stroke_width=5).set_points_as_corners(points)",
            "            load = Arrow(UP * 1.55, UP * 0.82, color=RED_C, stroke_width=6, buff=0)",
            "            return VGroup(spring, load, cn('弹性压缩与回弹', 21, GREEN_B).shift(RIGHT * 2.4 + DOWN * 0.85))",
            "",
            "        def construction_machine():",
            "            body = RoundedRectangle(width=1.65, height=0.62, corner_radius=0.08, color=BLUE_C, fill_color='#12324a', fill_opacity=0.85).shift(UP * 1.35)",
            "            cabin = Rectangle(width=0.46, height=0.42, color=BLUE_B, fill_opacity=0.65).next_to(body, UP, buff=0.02).shift(LEFT * 0.35)",
            "            tampers = VGroup(*[Line(body.get_bottom() + RIGHT * x, body.get_bottom() + RIGHT * x + DOWN * 1.18, color=YELLOW, stroke_width=5) for x in [-0.45, 0, 0.45]])",
            "            return VGroup(body, cabin, tampers, cn('捣固 / 稳定 / 整形机具', 20, YELLOW).next_to(body, UP, buff=0.16))",
            "",
            "        def comparison_view(labels):",
            "            left = VGroup(Polygon(LEFT * 2.9 + DOWN * 0.9, LEFT * 0.6 + DOWN * 0.9, LEFT * 0.95 + UP * 0.25, LEFT * 2.55 + UP * 0.25, color=ORANGE, fill_opacity=0.65), cn(labels[0], 20, ORANGE).shift(LEFT * 1.75 + DOWN * 1.25))",
            "            right = VGroup(Rectangle(width=2.35, height=0.42, color=GRAY_B, fill_opacity=0.65).shift(RIGHT * 1.75 + DOWN * 0.25), cn(labels[1], 20, GRAY_B).shift(RIGHT * 1.75 + DOWN * 1.25))",
            "            return VGroup(left, right)",
            "",
            "        def relation_flow(labels):",
            "            nodes = VGroup()",
            "            for i, text in enumerate(labels[:4]):",
            "                box = RoundedRectangle(width=1.45, height=0.58, corner_radius=0.08, color=[BLUE_C, GREEN_B, YELLOW, ORANGE][i], fill_opacity=0.18).shift(LEFT * 3.0 + RIGHT * i * 2.0 + UP * 0.1)",
            "                nodes.add(VGroup(box, cn(text, 18, WHITE).move_to(box)))",
            "            arrows = VGroup(*[Arrow(nodes[i].get_right(), nodes[i+1].get_left(), color=GRAY_B, buff=0.08) for i in range(len(nodes)-1)])",
            "            return VGroup(nodes, arrows)",
        ]
        for scene in plan.scenes:
            wait_time = max(1.5, min(float(scene.estimated_seconds) - 4.0, 3.5 if compact_timing else 16.0))
            title = json.dumps(f"{scene.index}. {scene.title}"[:56], ensure_ascii=True)
            narration = json.dumps(scene.narration[:82], ensure_ascii=True)
            visual = json.dumps(scene.visual_plan[:78], ensure_ascii=True)
            scene_text = (scene.title + " " + scene.narration + " " + scene.visual_plan).lower()
            color = "YELLOW" if scene.index % 3 == 1 else ("BLUE" if scene.index % 3 == 2 else "GREEN")
            labels = json.dumps(self._labels_from_scene(scene), ensure_ascii=True)
            lines.extend([
                "        clear_active()",
                f"        beat_title = cn({title}, font_size=24, color={color}).to_edge(LEFT).shift(UP * 2.72)",
                f"        beat_note = cn({narration}, font_size=19, color=WHITE).next_to(beat_title, DOWN, aligned_edge=LEFT)",
                f"        beat_visual = cn({visual}, font_size=17, color=GRAY_A).next_to(beat_note, DOWN, aligned_edge=LEFT, buff=0.12)",
                "        panel = VGroup(beat_title, beat_note, beat_visual)",
                "        self.play(FadeIn(panel, shift=UP * 0.15), run_time=0.8)",
                f"        scene_dots[{max(0, scene.index - 1) % max(1, len(plan.scenes))}].set_color(YELLOW).scale(1.35)",
            ])
            if any(keyword in scene_text for keyword in ["断面", "分层", "道床", "道砟", "轨枕", "钢轨", "路基", "ballast", "subgrade", "rail", "sleeper"]):
                lines.extend(["        active = layered_section()", "        self.play(Create(active[0]), Create(active[1]), LaggedStart(*[FadeIn(m) for m in active[2]], lag_ratio=0.04), Create(active[3]), FadeIn(active[4]), run_time=1.8)"])
                if any(keyword in scene_text for keyword in ["碎石", "颗粒", "道砟", "卵石", "空隙", "dirty", "particle"]):
                    lines.extend(["        particles = ballast_particles()", "        active.add(particles)", "        self.play(LaggedStart(*[FadeIn(p) for p in particles], lag_ratio=0.01), run_time=0.9)"])
            elif any(keyword in scene_text for keyword in ["荷载", "应力", "传递", "扩散", "压力", "受力", "轮载", "load", "stress", "force"]):
                lines.extend(["        active = VGroup(layered_section(), force_path())", "        self.play(FadeIn(active[0]), run_time=0.9)", "        self.play(LaggedStart(*[GrowArrow(a) for a in active[1][0]], lag_ratio=0.16), FadeIn(active[1][1:]), run_time=1.5)"])
            elif any(keyword in scene_text for keyword in ["排水", "雨", "水流", "空隙", "横坡", "drainage", "water"]):
                lines.extend(["        active = VGroup(layered_section(), drainage_path())", "        self.play(FadeIn(active[0]), run_time=0.9)", "        self.play(LaggedStart(*[FadeIn(d) for d in active[1][0]], lag_ratio=0.1), LaggedStart(*[GrowArrow(a) for a in active[1][1]], lag_ratio=0.15), FadeIn(active[1][2]), run_time=1.4)"])
            elif any(keyword in scene_text for keyword in ["弹性", "缓冲", "压缩", "回弹", "振动", "elastic", "spring"]):
                lines.extend(["        active = VGroup(layered_section(), elastic_spring())", "        self.play(FadeIn(active[0]), Create(active[1][0]), GrowArrow(active[1][1]), FadeIn(active[1][2]), run_time=1.5)", "        self.play(active[1][0].animate.scale(0.72, about_edge=DOWN), run_time=0.45)", "        self.play(active[1][0].animate.scale(1.38, about_edge=DOWN), run_time=0.55)"])
            elif any(keyword in scene_text for keyword in ["施工", "铺砟", "捣固", "稳定", "整形", "机具", "机械", "机床", "tamping", "machine"]):
                lines.extend(["        active = VGroup(layered_section(), construction_machine())", "        self.play(FadeIn(active[0]), FadeIn(active[1][0]), FadeIn(active[1][1]), FadeIn(active[1][3]), run_time=1.2)", "        self.play(LaggedStart(*[Create(t) for t in active[1][2]], lag_ratio=0.08), run_time=0.7)", "        self.play(active[1][2].animate.shift(DOWN * 0.28), run_time=0.35)", "        self.play(active[1][2].animate.shift(UP * 0.28), run_time=0.35)"])
            elif any(keyword in scene_text for keyword in ["对比", "类型", "分类", "有砟", "无砟", "比较", "compare", "type"]):
                lines.extend([f"        active = comparison_view({labels})", "        self.play(FadeIn(active[0], shift=LEFT * 0.2), FadeIn(active[1], shift=RIGHT * 0.2), run_time=1.2)", "        self.play(Circumscribe(active[0], color=ORANGE), Circumscribe(active[1], color=GRAY_B), run_time=1.1)"])
            else:
                lines.extend([f"        active = relation_flow({labels})", "        self.play(LaggedStart(*[FadeIn(node) for node in active[0]], lag_ratio=0.12), LaggedStart(*[GrowArrow(a) for a in active[1]], lag_ratio=0.12), run_time=1.4)", "        self.play(Circumscribe(active, color=BLUE_C), run_time=0.8)"])
            lines.extend([f"        self.wait({wait_time:.2f})", "        self.play(FadeOut(panel), run_time=0.45)"])
        lines.extend([
            "        summary = VGroup(cn(\"\\u5206\\u955c\\u6f14\\u793a\\u5b8c\\u6210\", font_size=34, color=YELLOW), cn(\"\\u753b\\u9762\\u5143\\u7d20\\u6765\\u81ea\\u5f53\\u524d\\u6559\\u5b66\\u8ba1\\u5212\\u548c\\u5206\\u955c\\u6587\\u672c\\u3002\", font_size=24, color=WHITE), cn(\"\\u672a\\u4f7f\\u7528\\u65e7\\u4e3b\\u9898\\u7d20\\u6750\\u6216\\u6570\\u5b66\\u5360\\u4f4d\\u56fe\\u3002\", font_size=22, color=GRAY_A)).arrange(DOWN, buff=0.25).move_to(ORIGIN)",
            "        clear_active()",
            "        self.play(FadeOut(timeline_group), ReplacementTransform(title, summary[0]), FadeIn(summary[1:]), run_time=1.6)",
            "        self.wait(3)",
            "",
        ])
        return "\n".join(lines)

    def _code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        # ManimCat-style fallback: one stable compiler, all content comes from the current storyboard.
        return self._generic_code_from_storyboard(plan, total_duration_seconds)

    def _cable_stayed_bridge_code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Builds a cable-stayed bridge fallback with structural visuals, not generic cards."""

        compact_timing = "COMPACT_TIMING" in plan.code_plan or "compact timing" in plan.code_plan.lower()
        safe_goal = plan.teaching_goal.replace("\\", "\\\\")[:96]
        lines = [
            "from manim import *",
            "import numpy as np",
            "",
            "",
            "def cn(text, font_size=24, color=WHITE):",
            "    return Text(text, font=\"Microsoft YaHei\", font_size=font_size, color=color)",
            "",
            "",
            "class GeneratedTeachingScene(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = '#0b1020'",
            f"        title = cn({json.dumps(safe_goal, ensure_ascii=True)}, font_size=27, color=WHITE).to_edge(UP)",
            "        subtitle = cn('斜拉桥结构可视化：桥塔、主梁、斜拉索、荷载与索力路径', font_size=18, color=GRAY_A).next_to(title, DOWN, buff=0.10)",
            "        self.play(Write(title), FadeIn(subtitle, shift=DOWN * 0.1), run_time=1.1)",
            "",
            "        deck = Rectangle(width=8.8, height=0.16, color=ORANGE, fill_color=ORANGE, fill_opacity=0.72).shift(DOWN * 1.35)",
            "        tower = Rectangle(width=0.32, height=3.7, color=BLUE_C, fill_color=BLUE_E, fill_opacity=0.52).shift(UP * 0.25)",
            "        tower_cap = Triangle(color=BLUE_C, fill_color=BLUE_E, fill_opacity=0.52).scale(0.26).rotate(PI).next_to(tower, UP, buff=0)",
            "        pier = Rectangle(width=0.62, height=0.55, color=GRAY_B, fill_color=GRAY_E, fill_opacity=0.35).next_to(deck, DOWN, buff=0.02)",
            "        bridge_base = VGroup(deck, tower, tower_cap, pier)",
            "        anchor_points = [np.array([x, -1.25, 0]) for x in [-4.0, -3.1, -2.2, -1.3, 1.3, 2.2, 3.1, 4.0]]",
            "        tower_points = [np.array([0, y, 0]) for y in [1.95, 1.66, 1.37, 1.08, 1.08, 1.37, 1.66, 1.95]]",
            "        stay_cables = VGroup(*[Line(tower_points[i], anchor_points[i], color=TEAL_C, stroke_width=3.2) for i in range(len(anchor_points))])",
            "        anchor_dots = VGroup(*[Dot(p, radius=0.045, color=YELLOW) for p in anchor_points], *[Dot(p, radius=0.045, color=YELLOW) for p in tower_points])",
            "        tower_label = cn('桥塔', font_size=22, color=BLUE_C).next_to(tower, RIGHT, buff=0.12).shift(UP * 0.7)",
            "        deck_label = cn('主梁 / 桥面', font_size=22, color=ORANGE).next_to(deck, DOWN, buff=0.22)",
            "        cable_label = cn('斜拉索', font_size=22, color=TEAL_C).move_to(LEFT * 2.55 + UP * 1.15)",
            "        cable_pointer = Arrow(cable_label.get_right() + RIGHT * 0.08, LEFT * 1.35 + UP * 1.25, color=TEAL_C, buff=0.02)",
            "        bridge_group = VGroup(bridge_base, stay_cables, anchor_dots, tower_label, deck_label, cable_label, cable_pointer)",
            "        self.play(Create(deck), Create(tower), FadeIn(tower_cap), FadeIn(pier), run_time=1.2)",
            "        self.play(LaggedStart(*[Create(c) for c in stay_cables], lag_ratio=0.06), FadeIn(anchor_dots), run_time=1.8)",
            "        self.play(FadeIn(tower_label), FadeIn(deck_label), FadeIn(cable_label), GrowArrow(cable_pointer), run_time=0.8)",
            "",
            "        load_arrows = VGroup(*[Arrow(np.array([x, -0.65, 0]), np.array([x, -1.15, 0]), color=RED_C, buff=0, stroke_width=5) for x in [-3.4, -1.7, 1.7, 3.4]])",
            "        load_label = cn('车辆荷载', font_size=22, color=RED_C).next_to(load_arrows, UP, buff=0.10)",
            "        force_arrows = VGroup(Arrow(LEFT * 3.2 + DOWN * 1.0, LEFT * 0.15 + UP * 1.65, color=YELLOW, buff=0.02, stroke_width=5), Arrow(RIGHT * 3.2 + DOWN * 1.0, RIGHT * 0.15 + UP * 1.65, color=YELLOW, buff=0.02, stroke_width=5))",
            "        force_label = cn('索力把荷载拉向桥塔', font_size=21, color=YELLOW).move_to(RIGHT * 2.7 + UP * 1.35)",
            "        compression_arrow = Arrow(UP * 1.7, DOWN * 0.85, color=PURPLE_B, buff=0.02, stroke_width=6)",
            "        compression_label = cn('桥塔受压', font_size=21, color=PURPLE_B).next_to(compression_arrow, RIGHT, buff=0.14)",
            "",
            "        diagram_origin = RIGHT * 3.15 + DOWN * 0.25",
            "        diag_cable = Arrow(diagram_origin, diagram_origin + LEFT * 1.25 + UP * 1.0, color=YELLOW, buff=0, stroke_width=5)",
            "        diag_fx = Arrow(diagram_origin, diagram_origin + LEFT * 1.25, color=BLUE_C, buff=0, stroke_width=5)",
            "        diag_fy = Arrow(diagram_origin, diagram_origin + UP * 1.0, color=GREEN_B, buff=0, stroke_width=5)",
            "        decomposition = VGroup(diag_cable, diag_fx, diag_fy, cn('T', 22, YELLOW).next_to(diag_cable, UP, buff=0.05), cn('水平分力', 18, BLUE_C).next_to(diag_fx, DOWN, buff=0.05), cn('竖向分力', 18, GREEN_B).next_to(diag_fy, RIGHT, buff=0.06))",
            "",
            "        fan_layout = VGroup(Rectangle(width=1.45, height=0.08, color=ORANGE).shift(LEFT * 3.6 + DOWN * 2.65), Line(LEFT * 3.6 + DOWN * 1.55, LEFT * 4.2 + DOWN * 2.6, color=TEAL_C), Line(LEFT * 3.6 + DOWN * 1.55, LEFT * 3.6 + DOWN * 2.6, color=TEAL_C), Line(LEFT * 3.6 + DOWN * 1.55, LEFT * 3.0 + DOWN * 2.6, color=TEAL_C), cn('扇形布置', 18, TEAL_C).shift(LEFT * 3.6 + DOWN * 2.95))",
            "        harp_layout = VGroup(Rectangle(width=1.45, height=0.08, color=ORANGE).shift(LEFT * 1.55 + DOWN * 2.65), Line(LEFT * 2.05 + DOWN * 1.55, LEFT * 2.55 + DOWN * 2.6, color=TEAL_C), Line(LEFT * 1.65 + DOWN * 1.55, LEFT * 2.15 + DOWN * 2.6, color=TEAL_C), Line(LEFT * 1.25 + DOWN * 1.55, LEFT * 1.75 + DOWN * 2.6, color=TEAL_C), cn('竖琴形布置', 18, TEAL_C).shift(LEFT * 1.55 + DOWN * 2.95))",
            "        layout_compare = VGroup(fan_layout, harp_layout)",
        ]
        for scene in plan.scenes:
            wait_time = max(1.5, min(float(scene.estimated_seconds) - 4.0, 3.5 if compact_timing else 24.0))
            title = json.dumps(f"{scene.index}. {scene.title[:34]}", ensure_ascii=True)
            narration = json.dumps(scene.narration[:66], ensure_ascii=True)
            scene_text = f"{scene.title}\n{scene.narration}\n{scene.visual_plan}".lower()
            lines.extend([
                f"        beat_title = cn({title}, font_size=24, color=YELLOW).to_edge(LEFT).shift(UP * 2.55)",
                f"        beat_note = cn({narration}, font_size=18, color=WHITE).next_to(beat_title, DOWN, aligned_edge=LEFT, buff=0.12)",
                "        panel = VGroup(beat_title, beat_note)",
                "        self.play(FadeIn(panel, shift=UP * 0.12), run_time=0.65)",
            ])
            if any(keyword in scene_text for keyword in ["荷载", "传递", "路径", "受力", "拉力", "索力", "load", "force", "tension"]):
                lines.extend([
                    "        self.play(FadeOut(decomposition), FadeOut(layout_compare), FadeIn(load_arrows), FadeIn(load_label), run_time=0.55)",
                    "        self.play(LaggedStart(*[Indicate(cable) for cable in stay_cables], lag_ratio=0.03), GrowArrow(force_arrows[0]), GrowArrow(force_arrows[1]), FadeIn(force_label), run_time=1.4)",
                    "        self.play(GrowArrow(compression_arrow), FadeIn(compression_label), run_time=0.8)",
                ])
            elif any(keyword in scene_text for keyword in ["分力", "分解", "水平", "竖向", "角度", "倾角", "component", "decompose"]):
                lines.extend([
                    "        self.play(FadeOut(load_arrows), FadeOut(load_label), FadeOut(force_arrows), FadeOut(force_label), FadeOut(compression_arrow), FadeOut(compression_label), FadeOut(layout_compare), run_time=0.45)",
                    "        self.play(Indicate(stay_cables[1]), Indicate(stay_cables[-2]), FadeIn(decomposition), run_time=1.2)",
                    "        self.play(Circumscribe(decomposition, color=YELLOW), run_time=1.0)",
                ])
            elif any(keyword in scene_text for keyword in ["布置", "扇形", "竖琴", "对称", "塔", "layout", "fan", "harp"]):
                lines.extend([
                    "        self.play(FadeOut(load_arrows), FadeOut(load_label), FadeOut(force_arrows), FadeOut(force_label), FadeOut(compression_arrow), FadeOut(compression_label), FadeOut(decomposition), run_time=0.45)",
                    "        self.play(FadeIn(layout_compare), Circumscribe(tower, color=BLUE_C), run_time=1.2)",
                    "        self.play(LaggedStart(*[Indicate(c) for c in stay_cables], lag_ratio=0.04), run_time=1.1)",
                ])
            else:
                lines.extend([
                    "        self.play(FadeOut(load_arrows), FadeOut(load_label), FadeOut(force_arrows), FadeOut(force_label), FadeOut(compression_arrow), FadeOut(compression_label), FadeOut(decomposition), FadeOut(layout_compare), run_time=0.45)",
                    "        self.play(Circumscribe(bridge_base, color=ORANGE), LaggedStart(*[Indicate(c) for c in stay_cables], lag_ratio=0.04), run_time=1.3)",
                ])
            lines.extend([f"        self.wait({wait_time:.2f})", "        self.play(FadeOut(panel), run_time=0.35)"])
        lines.extend([
            "        summary = VGroup(cn('斜拉桥的核心关系', font_size=34, color=YELLOW), cn('主梁承受荷载，斜拉索把拉力传给桥塔，桥塔再把压力传向基础。', font_size=24, color=WHITE), cn('后续每个分镜都应继续围绕真实结构运动，而不是抽象占位图。', font_size=21, color=GRAY_A)).arrange(DOWN, buff=0.25).move_to(ORIGIN)",
            "        self.play(FadeOut(bridge_group), FadeOut(load_arrows), FadeOut(load_label), FadeOut(force_arrows), FadeOut(force_label), FadeOut(compression_arrow), FadeOut(compression_label), FadeOut(decomposition), FadeOut(layout_compare), ReplacementTransform(title, summary[0]), FadeIn(summary[1:]), run_time=1.6)",
            "        self.wait(3)",
            "",
        ])
        return "\n".join(lines)


    def _country_code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Builds a country-overview fallback scene for China/nation introductions."""

        compact_timing = "COMPACT_TIMING" in plan.code_plan or "compact timing" in plan.code_plan.lower()
        safe_goal = plan.teaching_goal.replace("\\", "\\\\")[:96]
        lines = [
            "from manim import *",
            "",
            "",
            "def cn(text, font_size=24, color=WHITE):",
            "    return Text(text, font=\"Microsoft YaHei\", font_size=font_size, color=color)",
            "",
            "",
            "class GeneratedTeachingScene(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = \"#0b1020\"",
            f"        title = cn({json.dumps(safe_goal, ensure_ascii=True)}, font_size=28, color=WHITE).to_edge(UP)",
            "        subtitle = cn(\"\\u5730\\u7406\\u3001\\u5386\\u53f2\\u3001\\u6587\\u5316\\u4e0e\\u73b0\\u4ee3\\u53d1\\u5c55\", font_size=20, color=GRAY_A).next_to(title, DOWN, buff=0.12)",
            "        self.play(Write(title), FadeIn(subtitle, shift=DOWN * 0.12), run_time=1.2)",
            "",
            "        country_card = RoundedRectangle(width=4.8, height=3.2, corner_radius=0.12, color=RED_B, fill_color=\"#111827\", fill_opacity=0.86).shift(LEFT * 2.65 + DOWN * 0.15)",
            "        country_label = cn(\"\\u4e2d\\u56fd / \\u4e1c\\u4e9a\", font_size=25, color=YELLOW).next_to(country_card, UP, buff=0.12)",
            "        beijing_dot = Dot(country_card.get_center() + RIGHT * 0.65 + UP * 0.48, color=YELLOW, radius=0.08)",
            "        beijing_ring = Circle(radius=0.2, color=YELLOW).move_to(beijing_dot)",
            "        beijing_label = cn(\"\\u5317\\u4eac\", font_size=22, color=YELLOW).next_to(beijing_dot, RIGHT, buff=0.1)",
            "        east_arrow = Arrow(country_card.get_left() + LEFT * 0.25, country_card.get_right() + RIGHT * 0.25, buff=0, color=BLUE_C)",
            "        coast_label = cn(\"\\u592a\\u5e73\\u6d0b\\u897f\\u5cb8\", font_size=18, color=BLUE_C).next_to(country_card, DOWN, buff=0.12)",
            "        country_map = VGroup(country_card, country_label, beijing_dot, beijing_ring, beijing_label, east_arrow, coast_label)",
            "",
            "        topic_cards = VGroup()",
            "        topic_names = [\"\\u5730\\u7406\", \"\\u5386\\u53f2\", \"\\u6587\\u5316\", \"\\u73b0\\u4ee3\\u53d1\\u5c55\"]",
            "        for i, name in enumerate(topic_names):",
            "            card = RoundedRectangle(width=1.35, height=0.68, corner_radius=0.08, color=[BLUE_C, YELLOW, GREEN_B, ORANGE][i], fill_opacity=0.18)",
            "            label = cn(name, font_size=18, color=WHITE).move_to(card)",
            "            topic_cards.add(VGroup(card, label))",
            "        topic_cards.arrange_in_grid(rows=2, cols=2, buff=0.28).move_to(RIGHT * 2.75 + UP * 0.55)",
            "",
            "        timeline = Line(LEFT * 4.6, RIGHT * 4.6, color=GRAY_B).shift(DOWN * 2.35)",
            "        dynasties = [\"\\u590f\\u5546\\u5468\", \"\\u79e6\\u6c49\", \"\\u5510\\u5b8b\", \"\\u660e\\u6e05\", \"\\u73b0\\u4ee3\"]",
            "        timeline_nodes = VGroup()",
            "        for i, label in enumerate(dynasties):",
            "            x = -4.2 + i * 2.1",
            "            dot = Dot(np.array([x, -2.35, 0]), color=[BLUE_C, GREEN_B, YELLOW, ORANGE, RED_B][i])",
            "            text = cn(label, font_size=16, color=[BLUE_C, GREEN_B, YELLOW, ORANGE, RED_B][i]).next_to(dot, UP, buff=0.12)",
            "            timeline_nodes.add(VGroup(dot, text))",
            "        timeline_group = VGroup(timeline, timeline_nodes)",
            "",
            "        flag = Rectangle(width=2.55, height=1.55, color=RED, fill_color=RED_E, fill_opacity=0.85)",
            "        big_star = Star(n=5, outer_radius=0.22, color=YELLOW, fill_opacity=1).move_to(flag.get_center() + LEFT * 0.85 + UP * 0.35)",
            "        small_stars = VGroup(*[Star(n=5, outer_radius=0.09, color=YELLOW, fill_opacity=1).move_to(flag.get_center() + LEFT * 0.35 + UP * y) for y in [0.58, 0.28, -0.02, -0.32]])",
            "        flag_label = cn(\"\\u56fd\\u65d7\\u4e0e\\u9996\\u90fd\", font_size=21, color=YELLOW).next_to(flag, DOWN, buff=0.16)",
            "        flag_group = VGroup(flag, big_star, small_stars, flag_label).move_to(RIGHT * 2.75 + UP * 0.35)",
            "",
            "        culture_cards = VGroup()",
            "        culture_names = [\"\\u957f\\u57ce\", \"\\u4e1d\\u8def\", \"\\u56db\\u5927\\u53d1\\u660e\", \"\\u54f2\\u5b66\\u601d\\u60f3\"]",
            "        for i, name in enumerate(culture_names):",
            "            card = RoundedRectangle(width=1.55, height=0.62, corner_radius=0.08, color=[RED_B, ORANGE, BLUE_C, GREEN_B][i], fill_opacity=0.18)",
            "            label = cn(name, font_size=17, color=WHITE).move_to(card)",
            "            culture_cards.add(VGroup(card, label))",
            "        culture_cards.arrange_in_grid(rows=2, cols=2, buff=0.25).move_to(RIGHT * 2.75 + UP * 0.35)",
            "",
            "        bars = VGroup()",
            "        for i, height in enumerate([0.45, 0.9, 1.35, 1.75]):",
            "            bar = Rectangle(width=0.38, height=height, color=BLUE_C, fill_opacity=0.55).align_to(DOWN * 1.0, DOWN).shift(RIGHT * (1.65 + i * 0.55) + DOWN * 0.65)",
            "            bars.add(bar)",
            "        modern_label = cn(\"\\u7ecf\\u6d4e\\u3001\\u9ad8\\u94c1\\u3001\\u822a\\u5929\", font_size=21, color=BLUE_C).next_to(bars, DOWN, buff=0.22)",
            "        modern_group = VGroup(bars, modern_label)",
            "",
            "        self.play(FadeIn(country_map), FadeIn(topic_cards), Create(timeline), LaggedStart(*[FadeIn(node) for node in timeline_nodes], lag_ratio=0.12), run_time=2.0)",
            "",
        ]

        for scene in plan.scenes:
            wait_time = max(1.2, min(float(scene.estimated_seconds) - 4.0, 3.0 if compact_timing else 18.0))
            title = json.dumps(f"{scene.index}. {scene.title}"[:52], ensure_ascii=True)
            narration = json.dumps(scene.narration[:78], ensure_ascii=True)
            scene_text = (scene.title + " " + scene.narration + " " + scene.visual_plan).lower()
            color = "YELLOW" if scene.index % 3 == 1 else ("BLUE_C" if scene.index % 3 == 2 else "GREEN_B")
            lines.extend(
                [
                    f"        beat_title = cn({title}, font_size=24, color={color}).to_edge(LEFT).shift(UP * 2.72)",
                    f"        beat_note = cn({narration}, font_size=19, color=WHITE).next_to(beat_title, DOWN, aligned_edge=LEFT)",
                    "        panel = VGroup(beat_title, beat_note)",
                    "        self.play(FadeIn(panel, shift=UP * 0.12), run_time=0.6)",
                ]
            )
            if any(keyword in scene_text for keyword in ["flag", "capital", "beijing", "\u56fd\u65d7", "\u9996\u90fd", "\u5317\u4eac"]):
                lines.extend(["        self.play(FadeOut(topic_cards), FadeOut(culture_cards), FadeOut(modern_group), FadeIn(flag_group), run_time=0.8)", "        self.play(Indicate(beijing_dot), Circumscribe(flag_group, color=YELLOW), run_time=1.2)"])
            elif any(keyword in scene_text for keyword in ["history", "dynasty", "silk", "great wall", "invention", "culture", "\u5386\u53f2", "\u671d\u4ee3", "\u4e1d\u7ef8", "\u957f\u57ce", "\u53d1\u660e", "\u6587\u5316", "\u54f2\u5b66"]):
                lines.extend(["        self.play(FadeOut(topic_cards), FadeOut(flag_group), FadeOut(modern_group), FadeIn(culture_cards), run_time=0.8)", "        self.play(LaggedStart(*[Indicate(card) for card in culture_cards], lag_ratio=0.12), Indicate(timeline_nodes[min(3, len(timeline_nodes)-1)]), run_time=1.4)"])
            elif any(keyword in scene_text for keyword in ["gdp", "economy", "rail", "space", "technology", "\u7ecf\u6d4e", "\u9ad8\u94c1", "\u822a\u5929", "\u79d1\u6280", "\u73b0\u4ee3"]):
                lines.extend(["        self.play(FadeOut(topic_cards), FadeOut(flag_group), FadeOut(culture_cards), FadeIn(modern_group), run_time=0.8)", "        self.play(LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.08), Indicate(timeline_nodes[-1]), run_time=1.3)"])
            else:
                lines.extend(["        self.play(FadeOut(flag_group), FadeOut(culture_cards), FadeOut(modern_group), FadeIn(topic_cards), run_time=0.6)", "        self.play(Indicate(beijing_dot), Circumscribe(country_map, color=BLUE_C), LaggedStart(*[Indicate(card) for card in topic_cards], lag_ratio=0.1), run_time=1.4)"])
            lines.extend([f"        self.wait({wait_time:.2f})", "        self.play(FadeOut(panel), run_time=0.4)"])

        lines.extend(
            [
                "        final_summary = VGroup(",
                "            cn(\"\\u4e2d\\u56fd\\u6982\\u89c8\\u603b\\u7ed3\", font_size=34, color=YELLOW),",
                "            cn(\"\\u4ece\\u5730\\u7406\\u5b9a\\u4f4d\\uff0c\\u5230\\u5386\\u53f2\\u6587\\u5316\\uff0c\\u518d\\u5230\\u73b0\\u4ee3\\u53d1\\u5c55\\u3002\", font_size=24, color=WHITE),",
                "            cn(\"\\u4e2d\\u56fd = \\u5e7f\\u9614\\u7586\\u57df + \\u60a0\\u4e45\\u6587\\u660e + \\u73b0\\u4ee3\\u6d3b\\u529b\", font_size=24, color=WHITE),",
                "        ).arrange(DOWN, buff=0.25).move_to(ORIGIN)",
                "        self.play(FadeOut(country_map), FadeOut(topic_cards), FadeOut(timeline_group), FadeOut(flag_group), FadeOut(culture_cards), FadeOut(modern_group), run_time=0.8)",
                "        self.play(ReplacementTransform(title, final_summary[0]), FadeIn(final_summary[1:]), run_time=1.6)",
                "        self.wait(3)",
                "",
            ]
        )
        return "\n".join(lines)


    def _city_code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Builds a city/tourism/history fallback scene with topic-specific visuals."""

        compact_timing = "COMPACT_TIMING" in plan.code_plan or "compact timing" in plan.code_plan.lower()
        safe_goal = plan.teaching_goal.replace("\\", "\\\\")[:96]
        lines = [
            "from manim import *",
            "",
            "",
            "def cn(text, font_size=24, color=WHITE):",
            "    return Text(text, font=\"Microsoft YaHei\", font_size=font_size, color=color)",
            "",
            "",
            "class GeneratedTeachingScene(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = \"#0b1020\"",
            f"        title = cn({json.dumps(safe_goal, ensure_ascii=True)}, font_size=28, color=WHITE).to_edge(UP)",
            "        subtitle = cn(\"\\u57ce\\u5e02\\u5730\\u7406\\u3001\\u5386\\u53f2\\u8109\\u7edc\\u3001\\u4ea7\\u4e1a\\u4e0e\\u6587\\u65c5\\u7efc\\u5408\\u8bb2\\u89e3\", font_size=20, color=GRAY_A).next_to(title, DOWN, buff=0.12)",
            "        self.play(Write(title), FadeIn(subtitle, shift=DOWN * 0.12), run_time=1.2)",
            "",
            "        map_card = RoundedRectangle(width=4.4, height=3.1, corner_radius=0.12, color=BLUE_B, fill_color=\"#111827\", fill_opacity=0.82).shift(LEFT * 2.75 + DOWN * 0.15)",
            "        map_label = cn(\"\\u4e1c\\u5317 / \\u8fbd\\u5b81\", font_size=23, color=BLUE_C).next_to(map_card, UP, buff=0.12)",
            "        city_dot = Dot(map_card.get_center() + RIGHT * 0.45 + UP * 0.15, color=YELLOW, radius=0.09)",
            "        city_ring = Circle(radius=0.22, color=YELLOW).move_to(city_dot)",
            "        city_name = cn(\"\\u6c88\\u9633\", font_size=26, color=YELLOW).next_to(city_dot, RIGHT, buff=0.12)",
            "        hub_tags = VGroup(cn(\"\\u7701\\u4f1a\", font_size=18, color=WHITE), cn(\"\\u5386\\u53f2\\u540d\\u57ce\", font_size=18, color=WHITE), cn(\"\\u4ea4\\u901a\\u67a2\\u7ebd\", font_size=18, color=WHITE)).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(map_card, RIGHT, buff=0.28)",
            "        city_hub = VGroup(map_card, map_label, city_dot, city_ring, city_name, hub_tags)",
            "",
            "        timeline = Line(LEFT * 4.6, RIGHT * 4.6, color=GRAY_B).shift(DOWN * 2.35)",
            "        years = [\"\\u897f\\u6c49\", \"\\u76db\\u4eac\", \"\\u5de5\\u4e1a\\u57fa\\u5730\", \"\\u73b0\\u4ee3\\u6587\\u65c5\"]",
            "        timeline_nodes = VGroup()",
            "        for i, label in enumerate(years):",
            "            x = -4.1 + i * 2.75",
            "            dot = Dot(np.array([x, -2.35, 0]), color=[BLUE_C, YELLOW, ORANGE, GREEN_B][i])",
            "            text = cn(label, font_size=18, color=[BLUE_C, YELLOW, ORANGE, GREEN_B][i]).next_to(dot, UP, buff=0.12)",
            "            timeline_nodes.add(VGroup(dot, text))",
            "        timeline_group = VGroup(timeline, timeline_nodes)",
            "",
            "        palace_base = Rectangle(width=2.2, height=0.75, color=YELLOW, fill_opacity=0.28)",
            "        palace_roof = Triangle(color=RED_B, fill_opacity=0.65).scale(0.65).next_to(palace_base, UP, buff=0)",
            "        palace_label = cn(\"\\u6c88\\u9633\\u6545\\u5bab / \\u6e05\\u6587\\u5316\", font_size=21, color=YELLOW).next_to(palace_base, DOWN, buff=0.18)",
            "        palace_group = VGroup(palace_base, palace_roof, palace_label).move_to(RIGHT * 2.5 + UP * 0.35)",
            "",
            "        factory_body = Rectangle(width=2.35, height=0.75, color=ORANGE, fill_opacity=0.35)",
            "        chimney = Rectangle(width=0.28, height=1.2, color=ORANGE, fill_opacity=0.35).next_to(factory_body, UP, buff=0).shift(LEFT * 0.68)",
            "        gear = Circle(radius=0.36, color=BLUE_C).next_to(factory_body, RIGHT, buff=0.28)",
            "        gear_core = Circle(radius=0.13, color=BLUE_C, fill_opacity=0.55).move_to(gear)",
            "        factory_label = cn(\"\\u88c5\\u5907\\u5236\\u9020 / \\u5de5\\u4e1a\\u8f6c\\u578b\", font_size=21, color=ORANGE).next_to(factory_body, DOWN, buff=0.18)",
            "        industry_group = VGroup(factory_body, chimney, gear, gear_core, factory_label).move_to(RIGHT * 2.6 + UP * 0.25)",
            "",
            "        card_names = [\"\\u6545\\u5bab\", \"\\u5317\\u9675\", \"\\u5e05\\u5e9c\", \"\\u73b0\\u4ee3\\u57ce\\u5e02\"]",
            "        attraction_cards = VGroup()",
            "        for i, name in enumerate(card_names):",
            "            card = RoundedRectangle(width=1.35, height=0.75, corner_radius=0.08, color=[YELLOW, GREEN_B, BLUE_C, ORANGE][i], fill_opacity=0.18)",
            "            label = cn(name, font_size=18, color=WHITE).move_to(card)",
            "            attraction_cards.add(VGroup(card, label))",
            "        attraction_cards.arrange_in_grid(rows=2, cols=2, buff=0.28).move_to(RIGHT * 2.6 + UP * 0.25)",
            "",
            "        self.play(FadeIn(city_hub), Create(timeline), LaggedStart(*[FadeIn(node) for node in timeline_nodes], lag_ratio=0.15), run_time=2.0)",
            "",
        ]

        for scene in plan.scenes:
            wait_time = max(1.2, min(float(scene.estimated_seconds) - 4.0, 3.0 if compact_timing else 18.0))
            title = json.dumps(f"{scene.index}. {scene.title}"[:52], ensure_ascii=True)
            narration = json.dumps(scene.narration[:78], ensure_ascii=True)
            scene_text = (scene.title + " " + scene.narration + " " + scene.visual_plan).lower()
            color = "YELLOW" if scene.index % 3 == 1 else ("BLUE_C" if scene.index % 3 == 2 else "GREEN_B")
            lines.extend(
                [
                    f"        beat_title = cn({title}, font_size=24, color={color}).to_edge(LEFT).shift(UP * 2.72)",
                    f"        beat_note = cn({narration}, font_size=19, color=WHITE).next_to(beat_title, DOWN, aligned_edge=LEFT)",
                    "        panel = VGroup(beat_title, beat_note)",
                    "        self.play(FadeIn(panel, shift=UP * 0.12), run_time=0.6)",
                ]
            )
            if any(keyword in scene_text for keyword in ["history", "qing", "palace", "culture", "\u5386\u53f2", "\u6e05", "\u6545\u5bab", "\u6587\u5316", "\u76db\u4eac"]):
                lines.extend(
                    [
                        "        self.play(FadeOut(industry_group), FadeOut(attraction_cards), FadeIn(palace_group), run_time=0.8)",
                        "        self.play(Indicate(timeline_nodes[1]), Circumscribe(palace_group, color=YELLOW), run_time=1.2)",
                    ]
                )
            elif any(keyword in scene_text for keyword in ["industry", "factory", "manufacturing", "enterprise", "\u5de5\u4e1a", "\u5236\u9020", "\u4f01\u4e1a", "\u88c5\u5907", "\u8f6c\u578b"]):
                lines.extend(
                    [
                        "        self.play(FadeOut(palace_group), FadeOut(attraction_cards), FadeIn(industry_group), run_time=0.8)",
                        "        self.play(Rotate(gear, angle=PI / 2), Indicate(timeline_nodes[2]), Circumscribe(industry_group, color=ORANGE), run_time=1.3)",
                    ]
                )
            elif any(keyword in scene_text for keyword in ["tour", "travel", "landmark", "scenic", "\u65c5\u6e38", "\u666f\u70b9", "\u6587\u65c5", "\u5730\u6807", "\u5317\u9675", "\u5e05\u5e9c"]):
                lines.extend(
                    [
                        "        self.play(FadeOut(palace_group), FadeOut(industry_group), FadeIn(attraction_cards), run_time=0.8)",
                        "        self.play(LaggedStart(*[Indicate(card) for card in attraction_cards], lag_ratio=0.15), Indicate(timeline_nodes[3]), run_time=1.4)",
                    ]
                )
            else:
                lines.extend(
                    [
                        "        self.play(FadeOut(palace_group), FadeOut(industry_group), FadeOut(attraction_cards), run_time=0.5)",
                        "        self.play(Indicate(city_dot), Circumscribe(city_hub, color=BLUE_C), run_time=1.2)",
                    ]
                )
            lines.extend([f"        self.wait({wait_time:.2f})", "        self.play(FadeOut(panel), run_time=0.4)"])

        lines.extend(
            [
                "        final_summary = VGroup(",
                "            cn(\"\\u57ce\\u5e02\\u8bb2\\u89e3\\u7ed3\\u8bba\", font_size=34, color=YELLOW),",
                "            cn(\"\\u5148\\u5b9a\\u4f4d\\uff0c\\u518d\\u770b\\u5386\\u53f2\\u3001\\u4ea7\\u4e1a\\u548c\\u6587\\u65c5\\u3002\", font_size=24, color=WHITE),",
                "            cn(\"\\u6c88\\u9633 = \\u5386\\u53f2\\u539a\\u5ea6 + \\u5de5\\u4e1a\\u57fa\\u7840 + \\u73b0\\u4ee3\\u6d3b\\u529b\", font_size=24, color=WHITE),",
                "        ).arrange(DOWN, buff=0.25).move_to(ORIGIN)",
                "        self.play(FadeOut(city_hub), FadeOut(timeline_group), FadeOut(palace_group), FadeOut(industry_group), FadeOut(attraction_cards), run_time=0.8)",
                "        self.play(ReplacementTransform(title, final_summary[0]), FadeIn(final_summary[1:]), run_time=1.6)",
                "        self.wait(3)",
                "",
            ]
        )
        return "\n".join(lines)


    def _bilibili_code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Builds a topic-specific fallback scene for Bilibili/video-platform explanations."""

        compact_timing = "COMPACT_TIMING" in plan.code_plan or "compact timing" in plan.code_plan.lower()
        safe_goal = plan.teaching_goal.replace("\\", "\\\\").replace('"', "'")[:96]
        lines = [
            "from manim import *",
            "",
            "",
            "def cn(text, font_size=24, color=WHITE):",
            "    return Text(text, font=\"Microsoft YaHei\", font_size=font_size, color=color)",
            "",
            "",
            "class GeneratedTeachingScene(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = \"#0b1020\"",
            f"        title = cn({json.dumps(safe_goal, ensure_ascii=True)}, font_size=28, color=WHITE).to_edge(UP)",
            "        self.play(Write(title), run_time=1.0)",
            "",
            "        screen = RoundedRectangle(width=7.2, height=3.8, corner_radius=0.12, color=BLUE_B, fill_color=\"#111827\", fill_opacity=0.9).shift(DOWN * 0.35)",
            "        play = Triangle(color=WHITE, fill_opacity=0.9).scale(0.22).rotate(-PI / 2).move_to(screen.get_center())",
            "        progress = Line(screen.get_corner(DL) + RIGHT * 0.35 + UP * 0.28, screen.get_corner(DR) + LEFT * 0.35 + UP * 0.28, color=GRAY_B)",
            "        progress_fill = Line(progress.get_start(), progress.get_start() + RIGHT * 2.0, color=BLUE_C, stroke_width=6)",
            "        coin = Circle(radius=0.18, color=YELLOW, fill_opacity=0.8).move_to(RIGHT * 4.65 + DOWN * 1.7)",
            "        like = Star(n=5, outer_radius=0.2, color=YELLOW, fill_opacity=0.8).next_to(coin, LEFT, buff=0.35)",
            "        player = VGroup(screen, play, progress, progress_fill, coin, like)",
            "        self.play(FadeIn(screen), FadeIn(play), Create(progress), Create(progress_fill), run_time=1.3)",
            "",
            "        logo = VGroup(cn(\"bilibili\", font_size=42, color=BLUE_C), cn(\"\\u89c6\\u9891\\u5e73\\u53f0 / \\u5e74\\u8f7b\\u4eba\\u793e\\u533a\", font_size=22, color=GRAY_A)).arrange(DOWN, buff=0.15).move_to(LEFT * 3.1 + UP * 1.25)",
            "        self.play(FadeIn(logo, shift=UP * 0.15), FadeIn(coin), FadeIn(like), run_time=1.2)",
            "",
            "        danmaku = VGroup(cn(\"\\u524d\\u65b9\\u9ad8\\u80fd\", font_size=20, color=YELLOW), cn(\"\\u8fd9\\u5c31\\u662f\\u5f39\\u5e55\", font_size=20, color=GREEN_B), cn(\"\\u7237\\u9752\\u56de\", font_size=20, color=BLUE_C), cn(\"\\u77e5\\u8bc6\\u533a\\u6253\\u5361\", font_size=20, color=ORANGE))",
            "        for i, item in enumerate(danmaku):",
            "            item.move_to(screen.get_right() + RIGHT * (0.5 + i * 0.25) + UP * (1.1 - i * 0.55))",
            "",
            "        up_avatar = Circle(radius=0.45, color=GREEN_B, fill_opacity=0.45).move_to(LEFT * 3.1 + DOWN * 1.0)",
            "        up_label = cn(\"UP\\u4e3b\", font_size=24, color=GREEN_B).move_to(up_avatar)",
            "        creator = VGroup(up_avatar, up_label)",
            "        category_cards = VGroup(RoundedRectangle(width=1.35, height=0.55, corner_radius=0.08, color=BLUE_C).shift(RIGHT * 1.6 + UP * 1.15), RoundedRectangle(width=1.35, height=0.55, corner_radius=0.08, color=GREEN_B).shift(RIGHT * 3.1 + UP * 0.45), RoundedRectangle(width=1.35, height=0.55, corner_radius=0.08, color=ORANGE).shift(RIGHT * 2.05 + DOWN * 0.75))",
            "        category_labels = VGroup(cn(\"ACG\", font_size=20, color=WHITE).move_to(category_cards[0]), cn(\"\\u77e5\\u8bc6\", font_size=20, color=WHITE).move_to(category_cards[1]), cn(\"\\u751f\\u6d3b\", font_size=20, color=WHITE).move_to(category_cards[2]))",
            "        category_group = VGroup(category_cards, category_labels)",
            "        arrows = VGroup(*[Arrow(creator.get_right(), card.get_left(), buff=0.1, color=GRAY_A) for card in category_cards])",
            "",
            "        timeline = NumberLine(x_range=[2009, 2024, 5], length=5.2, color=GRAY_B, include_numbers=False).to_edge(DOWN).shift(UP * 0.2)",
            "        t2009 = cn(\"2009\\nACG\\u8d77\\u6b65\", font_size=18, color=BLUE_C).next_to(timeline.n2p(2009), UP)",
            "        t2024 = cn(\"\\u591a\\u5143\\u793e\\u533a\", font_size=18, color=YELLOW).next_to(timeline.n2p(2024), UP)",
            "        timeline_group = VGroup(timeline, t2009, t2024)",
            "",
        ]

        for scene in plan.scenes:
            wait_time = max(1.2, min(float(scene.estimated_seconds) - 4.0, 3.0 if compact_timing else 16.0))
            title = json.dumps(f"{scene.index}. {scene.title}"[:52], ensure_ascii=True)
            narration = json.dumps(scene.narration[:74], ensure_ascii=True)
            scene_text = (scene.title + " " + scene.narration + " " + scene.visual_plan).lower()
            color = "BLUE_C" if scene.index % 3 == 1 else ("YELLOW" if scene.index % 3 == 2 else "GREEN_B")
            lines.extend([
                f"        beat_title = cn({title}, font_size=24, color={color}).to_edge(LEFT).shift(UP * 2.72)",
                f"        beat_note = cn({narration}, font_size=19, color=WHITE).next_to(beat_title, DOWN, aligned_edge=LEFT)",
                "        panel = VGroup(beat_title, beat_note)",
                "        self.play(FadeIn(panel, shift=UP * 0.12), run_time=0.6)",
            ])
            if any(keyword in scene_text for keyword in ["\u5f39\u5e55", "danmaku", "comment", "screen"]):
                lines.extend(["        self.play(LaggedStart(*[FadeIn(item) for item in danmaku], lag_ratio=0.12), run_time=0.8)", "        self.play(*[item.animate.shift(LEFT * 7.8) for item in danmaku], run_time=2.4, rate_func=linear)", "        self.play(Circumscribe(screen, color=BLUE_C), run_time=0.8)"])
            elif any(keyword in scene_text for keyword in ["up", "creator", "\u521b\u4f5c", "up\u4e3b"]):
                lines.extend(["        self.play(FadeIn(creator), LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.15), FadeIn(category_group), run_time=1.6)", "        self.play(Indicate(creator), Circumscribe(category_group, color=GREEN_B), run_time=1.2)"])
            elif any(keyword in scene_text for keyword in ["acg", "\u77e5\u8bc6", "\u751f\u6d3b", "\u5206\u533a", "category"]):
                lines.extend(["        self.play(FadeIn(category_group), run_time=0.8)", "        self.play(LaggedStart(*[Indicate(card) for card in category_cards], lag_ratio=0.2), run_time=1.4)"])
            elif any(keyword in scene_text for keyword in ["2009", "\u5386\u53f2", "\u8d77\u6e90", "\u53d1\u5c55"]):
                lines.extend(["        self.play(Create(timeline), FadeIn(t2009), run_time=1.0)", "        self.play(FadeIn(t2024), timeline.animate.set_color(BLUE_C), run_time=1.0)"])
            else:
                lines.extend(["        self.play(Circumscribe(player, color=BLUE_C), Indicate(logo), run_time=1.2)", "        self.play(Indicate(coin), Indicate(like), run_time=0.8)"])
            lines.extend([f"        self.wait({wait_time:.2f})", "        self.play(FadeOut(panel), run_time=0.4)"])

        lines.extend(["        final_summary = VGroup(cn(\"Bilibili \\u7684\\u6838\\u5fc3\", font_size=34, color=BLUE_C), cn(\"\\u5f39\\u5e55\\u8ba9\\u89c2\\u770b\\u53d8\\u6210\\u5171\\u540c\\u53c2\\u4e0e\\u3002\", font_size=24, color=WHITE), cn(\"UP\\u4e3b\\u3001\\u5206\\u533a\\u548c\\u793e\\u533a\\u6587\\u5316\\u5171\\u540c\\u6784\\u6210\\u5185\\u5bb9\\u751f\\u6001\\u3002\", font_size=24, color=WHITE)).arrange(DOWN, buff=0.25).move_to(ORIGIN)", "        self.play(FadeOut(logo), FadeOut(player), FadeOut(creator), FadeOut(arrows), FadeOut(category_group), FadeOut(timeline_group), FadeOut(danmaku), run_time=0.8)", "        self.play(ReplacementTransform(title, final_summary[0]), FadeIn(final_summary[1:]), run_time=1.6)", "        self.wait(3)", ""])
        return "\n".join(lines)

    def _bridge_code_from_storyboard(self, plan: TeachingPlan, total_duration_seconds: int) -> str:
        """Builds a bridge-specific fallback scene instead of the generic vector template."""

        compact_timing = "COMPACT_TIMING" in plan.code_plan or "compact timing" in plan.code_plan.lower()
        safe_goal = plan.teaching_goal.replace("\\", "\\\\").replace('"', "'")[:96]
        lines = [
            "from manim import *",
            "",
            "",
            "def cn(text, font_size=24, color=WHITE):",
            "    return Text(text, font=\"Microsoft YaHei\", font_size=font_size, color=color)",
            "",
            "class GeneratedTeachingScene(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = \"#0b1020\"",
            f"        title = cn(\"{safe_goal}\", font_size=28, color=WHITE).to_edge(UP)",
            "        self.play(Write(title), run_time=1.2)",
            "",
            "        left_tower = Rectangle(width=0.28, height=3.1, color=RED_B, fill_opacity=0.35).move_to(LEFT * 4 + DOWN * 0.25)",
            "        right_tower = Rectangle(width=0.28, height=3.1, color=RED_B, fill_opacity=0.35).move_to(RIGHT * 4 + DOWN * 0.25)",
            "        deck = Rectangle(width=8.8, height=0.18, color=ORANGE, fill_opacity=0.65).move_to(DOWN * 1.65)",
            "        anchor_l = Triangle(color=GRAY_B, fill_opacity=0.6).scale(0.28).rotate(PI / 2).move_to(LEFT * 5.25 + DOWN * 1.65)",
            "        anchor_r = Triangle(color=GRAY_B, fill_opacity=0.6).scale(0.28).rotate(-PI / 2).move_to(RIGHT * 5.25 + DOWN * 1.65)",
            "        cable_points = [np.array([x, 0.34 * (x ** 2) - 0.35, 0]) for x in np.linspace(-4.6, 4.6, 48)]",
            "        main_cable = VMobject(color=BLUE_B, stroke_width=6).set_points_smoothly(cable_points)",
            "        hangers = VGroup(*[Line(np.array([x, 0.34 * (x ** 2) - 0.35, 0]), np.array([x, -1.56, 0]), color=GREEN_B, stroke_width=2) for x in np.linspace(-3.6, 3.6, 9)])",
            "        bridge = VGroup(left_tower, right_tower, deck, anchor_l, anchor_r, main_cable, hangers)",
            "        self.play(FadeIn(left_tower), FadeIn(right_tower), run_time=1.0)",
            "        self.play(Create(main_cable), FadeIn(anchor_l), FadeIn(anchor_r), run_time=1.4)",
            "        self.play(LaggedStart(*[Create(h) for h in hangers], lag_ratio=0.08), FadeIn(deck), run_time=1.7)",
            "",
            "        component_labels = VGroup(",
            "            cn(\"桥塔\", font_size=22, color=RED_B).next_to(left_tower, LEFT),",
            "            cn(\"主缆\", font_size=22, color=BLUE_B).move_to(UP * 2.0),",
            "            cn(\"吊索\", font_size=22, color=GREEN_B).move_to(RIGHT * 2.4 + DOWN * 0.45),",
            "            cn(\"桥面\", font_size=22, color=ORANGE).next_to(deck, DOWN),",
            "        )",
            "        self.play(LaggedStart(*[FadeIn(label) for label in component_labels], lag_ratio=0.18), run_time=1.8)",
            "        self.wait(2)",
            "        self.play(FadeOut(component_labels), run_time=0.6)",
            "",
            "        load_arrows = VGroup(*[Arrow(np.array([x, -0.65, 0]), np.array([x, -1.42, 0]), buff=0, color=YELLOW) for x in np.linspace(-3.4, 3.4, 5)])",
            "        hanger_arrows = VGroup(*[Arrow(np.array([x, -1.45, 0]), np.array([x, -0.55, 0]), buff=0, color=GREEN) for x in np.linspace(-3.0, 3.0, 4)])",
            "        tower_compression = VGroup(Arrow(LEFT * 4 + UP * 1.35, LEFT * 4 + DOWN * 1.35, buff=0, color=RED), Arrow(RIGHT * 4 + UP * 1.35, RIGHT * 4 + DOWN * 1.35, buff=0, color=RED))",
            "        parabola = VMobject(color=BLUE_C, stroke_width=5).set_points_smoothly([np.array([x, 0.23 * (x ** 2) - 0.55, 0]) for x in np.linspace(-4.4, 4.4, 48)])",
            "        catenary = VMobject(color=TEAL_C, stroke_width=5).set_points_smoothly([np.array([x, 0.45 * (np.cosh(x / 2.8) - 1) - 0.65, 0]) for x in np.linspace(-4.0, 4.0, 48)])",
            "        equation_box = VGroup(",
            "            cn(\"均布桥面荷载 -> 抛物线\", font_size=24, color=BLUE_C),",
            "            cn(\"主缆自重 -> 悬链线\", font_size=24, color=TEAL_C),",
            "            cn(\"主缆受拉，桥塔受压\", font_size=24, color=WHITE),",
            "        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).to_corner(UR).shift(DOWN * 0.55)",
            "",
        ]

        for scene in plan.scenes:
            wait_time = max(1.2, min(float(scene.estimated_seconds) - 5.0, 3.0 if compact_timing else 18.0))
            title = scene.title.replace("\\", "\\\\").replace('"', "'")[:58]
            narration = scene.narration.replace("\\", "\\\\").replace('"', "'")[:86]
            text = (scene.title + " " + scene.narration + " " + scene.visual_plan).lower()
            color = "YELLOW" if scene.index % 3 == 1 else ("BLUE_B" if scene.index % 3 == 2 else "GREEN_B")
            lines.extend(
                [
                    f"        beat_title = cn(\"{scene.index}. {title}\", font_size=24, color={color}).to_edge(LEFT).shift(UP * 2.75)",
                    f"        beat_note = cn(\"{narration}\", font_size=20, color=WHITE).next_to(beat_title, DOWN, aligned_edge=LEFT)",
                    "        panel = VGroup(beat_title, beat_note)",
                    "        self.play(FadeIn(panel, shift=UP * 0.12), run_time=0.7)",
                ]
            )
            if any(keyword in text for keyword in ["load", "path", "force flow", "traffic", "deck carries", "荷载", "传力", "力流", "车辆", "桥面承载"]):
                lines.extend(
                    [
                        "        self.play(LaggedStart(*[GrowArrow(a) for a in load_arrows], lag_ratio=0.12), run_time=1.4)",
                        "        self.play(LaggedStart(*[GrowArrow(a) for a in hanger_arrows], lag_ratio=0.12), run_time=1.2)",
                        "        self.play(LaggedStart(*[GrowArrow(a) for a in tower_compression], lag_ratio=0.15), run_time=1.0)",
                    ]
                )
            elif any(keyword in text for keyword in ["catenary", "parabola", "shape", "uniform load", "self-weight", "悬链线", "抛物线", "线形", "均布", "自重"]):
                lines.extend(
                    [
                        "        self.play(Transform(main_cable.copy().set_opacity(0), parabola), run_time=0.1)",
                        "        self.play(Create(parabola), run_time=1.2)",
                        "        self.play(Create(catenary), FadeIn(equation_box[:2]), run_time=1.4)",
                        "        self.play(Indicate(parabola), Indicate(catenary), run_time=1.2)",
                    ]
                )
            elif any(keyword in text for keyword in ["tension", "compression", "tower", "cable segment", "equilibrium", "受拉", "受压", "桥塔", "主缆", "平衡"]):
                lines.extend(
                    [
                        "        self.play(main_cable.animate.set_stroke(width=9), Indicate(left_tower), Indicate(right_tower), run_time=1.3)",
                        "        self.play(LaggedStart(*[GrowArrow(a) for a in tower_compression], lag_ratio=0.15), FadeIn(equation_box[2]), run_time=1.2)",
                    ]
                )
            elif any(keyword in text for keyword in ["component", "tower", "hanger", "deck", "anchor", "构件", "桥塔", "吊索", "桥面", "锚碇"]):
                lines.extend(
                    [
                        "        self.play(Circumscribe(left_tower, color=RED_B), Circumscribe(right_tower, color=RED_B), run_time=1.0)",
                        "        self.play(Circumscribe(deck, color=ORANGE), Circumscribe(hangers, color=GREEN_B), run_time=1.1)",
                    ]
                )
            else:
                target = "main_cable" if scene.index % 3 == 1 else ("deck" if scene.index % 3 == 2 else "hangers")
                lines.append(f"        self.play(Circumscribe({target}, color={color}), run_time=1.2)")
            lines.extend(
                [
                    f"        self.wait({wait_time:.2f})",
                    "        self.play(FadeOut(panel), run_time=0.45)",
                ]
            )

        lines.extend(
            [
                "        final_summary = VGroup(",
                "            cn(\"悬索桥核心结论\", font_size=34, color=YELLOW),",
                "            cn(\"桥面荷载经吊索传入主缆拉力。\", font_size=24, color=WHITE),",
                "            cn(\"桥塔主要受压，主缆形状取决于荷载模型。\", font_size=24, color=WHITE),",
                "        ).arrange(DOWN, buff=0.25).move_to(ORIGIN)",
                "        self.play(FadeOut(load_arrows), FadeOut(hanger_arrows), FadeOut(tower_compression), FadeOut(parabola), FadeOut(catenary), FadeOut(equation_box), run_time=0.8)",
                "        self.play(bridge.animate.scale(0.78).to_edge(DOWN), ReplacementTransform(title, final_summary[0]), FadeIn(final_summary[1:]), run_time=2)",
                "        self.wait(4)",
                "",
            ]
        )
        return "\n".join(lines)

    def _fallback_code(self, teaching_goal: str, total_duration_seconds: int = 300) -> str:
        safe_goal = teaching_goal.replace("\\", "\\\\").replace('"', "'")[:120]
        target = max(300, int(total_duration_seconds))
        pause = max(3, min(32, round((target + 20) / 9, 2)))
        return f'''from manim import *


def cn(text, font_size=24, color=WHITE):
    return Text(text, font="Microsoft YaHei", font_size=font_size, color=color)


class GeneratedTeachingScene(Scene):
    def construct(self):
        self.camera.background_color = "#111827"
        title = cn("教学动画", font_size=42, color=WHITE).to_edge(UP)
        subtitle = cn("{safe_goal}", font_size=22, color=GRAY_B).next_to(title, DOWN)
        self.play(Write(title), FadeIn(subtitle, shift=DOWN), run_time=1.5)
        self.wait({pause})

        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 4, 1],
            x_length=6,
            y_length=4,
            axis_config={{"color": GRAY_B}},
        ).shift(DOWN * 0.4)
        x_label = cn("x", font_size=24, color=GRAY_B).next_to(axes.x_axis.get_end(), DOWN)
        y_label = cn("y", font_size=24, color=GRAY_B).next_to(axes.y_axis.get_end(), LEFT)
        labels = VGroup(x_label, y_label)
        self.play(Create(axes), FadeIn(labels), run_time=1.5)
        self.wait({pause})

        origin = axes.c2p(0, 0)
        endpoint = axes.c2p(3.6, 2.4)
        v = Arrow(origin, endpoint, buff=0, color=YELLOW)
        base = Line(origin, axes.c2p(3.6, 0), color=BLUE)
        height = DashedLine(axes.c2p(3.6, 0), endpoint, color=GREEN)
        dot = Dot(endpoint, color=RED)
        self.play(GrowArrow(v), Create(base), Create(height), FadeIn(dot), run_time=2)
        self.wait({pause})

        formula = cn("v = x i + y j", font_size=38, color=WHITE)
        formula.to_edge(DOWN)
        self.play(Write(formula), run_time=1.5)
        self.wait({pause})

        focus = SurroundingRectangle(formula, color=YELLOW, buff=0.18)
        note = cn("图形解释公式", font_size=26, color=YELLOW).next_to(formula, UP)
        self.play(Create(focus), FadeIn(note), Circumscribe(v), run_time=2)
        self.wait({pause})

        projection_label = cn("投影是沿 x 方向看得见的部分", font_size=26, color=BLUE).next_to(base, DOWN)
        self.play(FadeIn(projection_label), base.animate.set_stroke(width=8), run_time=2)
        self.wait({pause})

        compare_label = cn("原向量和它的影子并不相同", font_size=25, color=GREEN).to_edge(LEFT).shift(DOWN * 2.6)
        self.play(FadeIn(compare_label), v.animate.set_color(YELLOW), height.animate.set_color(GREEN), run_time=2)
        self.wait({pause})

        mistake = cn("检查：方向很重要", font_size=30, color=RED).next_to(note, UP)
        self.play(FadeIn(mistake), Circumscribe(base), run_time=2)
        self.wait({pause})

        summary = VGroup(
            cn("核心想法", font_size=34, color=YELLOW),
            cn("把对象拆成可以看见的部分。", font_size=26, color=WHITE),
        ).arrange(DOWN, buff=0.25).move_to(ORIGIN)
        self.play(
            FadeOut(axes), FadeOut(labels), FadeOut(v), FadeOut(base), FadeOut(height), FadeOut(dot),
            FadeOut(formula), FadeOut(focus), FadeOut(note), FadeOut(projection_label), FadeOut(compare_label), FadeOut(mistake),
            ReplacementTransform(title, summary[0]),
            ReplacementTransform(subtitle, summary[1]),
            run_time=2,
        )
        self.wait({pause})
'''
