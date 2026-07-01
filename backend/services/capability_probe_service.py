from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from backend.ai.capabilities import CapabilityProbeResult, ModelCapabilities, ModelProfile, utc_now_iso


_ONE_PIXEL_PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
).decode("ascii")


class CapabilityProbeService:
    """Best-effort probes; unknown capabilities remain user-configurable."""

    async def probe(self, profile: ModelProfile) -> tuple[ModelCapabilities, CapabilityProbeResult]:
        if profile.provider_name.lower() == "mock":
            capabilities = ModelCapabilities(text_generation=True, json_output=True)
            return capabilities, CapabilityProbeResult(
                status="success",
                tested_at=utc_now_iso(),
                message="本地 Mock 能力来自内置实现。",
                detected=capabilities.model_dump(),
            )

        headers = {"Content-Type": "application/json", **profile.parameters.extra_headers}
        if profile.api_key:
            headers.setdefault("Authorization", f"Bearer {profile.api_key}")
        url = profile.api_base_url.rstrip("/") + "/chat/completions"
        details: dict[str, str] = {}
        detected: dict[str, bool] = {}
        timeout = httpx.Timeout(connect=12, read=45, write=20, pool=10)

        async with httpx.AsyncClient(timeout=timeout) as client:
            text_payload = self._base_payload(profile, "只回复 OK")
            detected["text_generation"] = await self._try(client, url, headers, text_payload, "text_generation", details)

            json_payload = self._base_payload(profile, "仅返回 JSON：{\"ok\":true}")
            json_payload["response_format"] = {"type": "json_object"}
            detected["json_output"] = await self._try(client, url, headers, json_payload, "json_output", details)

            function_payload = self._base_payload(profile, "调用 ping 工具")
            function_payload["tools"] = [{"type": "function", "function": {"name": "ping", "description": "connectivity probe", "parameters": {"type": "object", "properties": {}}}}]
            function_payload["tool_choice"] = "auto"
            detected["function_calling"] = await self._try(client, url, headers, function_payload, "function_calling", details)

            stream_payload = self._base_payload(profile, "只回复 OK")
            stream_payload["stream"] = True
            detected["streaming"] = await self._try_stream(client, url, headers, stream_payload, details)

            vision_payload = self._base_payload(profile, [
                {"type": "text", "text": "这是一张测试图片吗？只回复是。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_ONE_PIXEL_PNG}"}},
            ])
            detected["vision"] = await self._try(client, url, headers, vision_payload, "vision", details)

        vision = detected.get("vision", False)
        capabilities = ModelCapabilities(
            text_generation=detected.get("text_generation", False),
            vision=vision,
            image_upload=vision,
            multimodal_input=vision,
            image_annotation=vision,
            function_calling=detected.get("function_calling", False),
            json_output=detected.get("json_output", False),
            streaming=detected.get("streaming", False),
            audio=profile.capabilities.audio,
        ).normalize()
        succeeded = sum(1 for value in detected.values() if value)
        status = "success" if succeeded == len(detected) else ("partial" if succeeded else "failed")
        return capabilities, CapabilityProbeResult(
            status=status,
            tested_at=utc_now_iso(),
            message=f"能力探测完成：{succeeded}/{len(detected)} 项通过；未通过项仍可手动配置。",
            detected=detected,
            details=details,
        )

    def _base_payload(self, profile: ModelProfile, content: str | list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": profile.model_name,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": min(32, profile.parameters.max_tokens),
        }

    async def _try(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        name: str,
        details: dict[str, str],
    ) -> bool:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.is_success:
                data = response.json()
                choices = data.get("choices") or []
                passed = bool(choices)
                message = choices[0].get("message", {}) if choices else {}
                if name == "json_output" and passed:
                    try:
                        json_content = message.get("content") or ""
                        json.loads(json_content)
                    except (TypeError, ValueError):
                        passed = False
                elif name == "function_calling" and passed:
                    passed = bool(message.get("tool_calls") or message.get("function_call"))
                details[name] = f"HTTP {response.status_code}"
                return passed
            details[name] = f"HTTP {response.status_code}: {response.text[:240]}"
        except Exception as exc:
            details[name] = str(exc)
        return False

    async def _try_stream(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        details: dict[str, str],
    ) -> bool:
        try:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if not response.is_success:
                    details["streaming"] = f"HTTP {response.status_code}"
                    return False
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        details["streaming"] = f"HTTP {response.status_code}, stream data received"
                        return True
        except Exception as exc:
            details["streaming"] = str(exc)
        return False
