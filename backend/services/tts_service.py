import base64
import hashlib
import hmac
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import websocket

from backend.core.config import Settings


@dataclass
class TTSResult:
    """Paths and status produced by narration synthesis."""

    enabled: bool
    audio_path: Path | None = None
    muxed_video_path: Path | None = None
    error: str | None = None
    status: str = "disabled"
    message: str = "配音未启用。"


class TTSService:
    """Fish Audio first, with the older Xunfei WebSocket path kept as fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return self._fish_configured() or self._xunfei_configured()

    def synthesize_segment_audio(self, text: str, output_path: Path) -> TTSResult:
        """Synthesize one segment narration without concatenating or muxing project media."""

        if not self.is_configured():
            return TTSResult(enabled=False, status="disabled")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and output_path.stat().st_size > 0:
            return TTSResult(enabled=True, audio_path=output_path, status="cached", message="Segment audio reused.")
        try:
            self._synthesize_text_with_fallback(text.strip(), output_path)
            return TTSResult(enabled=True, audio_path=output_path, status="ready", message="Segment audio ready.")
        except Exception as exc:
            return TTSResult(enabled=True, status="failed", error=str(exc), message="Segment audio synthesis failed.")

    def synthesize_project_audio(
        self,
        *,
        scene_narrations: list[str],
        project_dir: Path,
        video_path: Path | None,
    ) -> TTSResult:
        """Synthesize narration audio and optionally mux it into the rendered mp4."""

        if not self.is_configured():
            return TTSResult(enabled=False)

        provider = "fish" if self._fish_configured() else "xunfei"
        try:
            audio_dir = project_dir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            narration_text = "\n".join(text.strip() for text in scene_narrations if text.strip())
            (audio_dir / "narration_text.txt").write_text(narration_text, encoding="utf-8")

            scene_audio_paths: list[Path] = []
            for index, text in enumerate(scene_narrations, start=1):
                clean_text = text.strip()
                if not clean_text:
                    continue
                output_path = audio_dir / f"scene_{index:02d}.mp3"
                if provider == "fish":
                    self._synthesize_text_fish(clean_text, output_path)
                else:
                    self._synthesize_text_xunfei(clean_text, output_path)
                scene_audio_paths.append(output_path)

            if not scene_audio_paths:
                return TTSResult(
                    enabled=True,
                    status="failed",
                    error="没有可合成的旁白文本。",
                    message="配音生成失败：没有可合成的旁白文本。",
                )

            combined_audio = audio_dir / "narration_combined.mp3"
            self._concat_audio(scene_audio_paths, combined_audio)

            if not video_path or not video_path.exists():
                return TTSResult(
                    enabled=True,
                    audio_path=combined_audio,
                    status="audio_only",
                    message="配音文件已生成，但没有可嵌入的视频。",
                )

            muxed_video = project_dir / "outputs" / "animation_with_audio.mp4"
            try:
                self._mux_audio_video(video_path, combined_audio, muxed_video)
                return TTSResult(
                    enabled=True,
                    audio_path=combined_audio,
                    muxed_video_path=muxed_video,
                    status="embedded",
                    message="配音已生成并嵌入视频。",
                )
            except Exception as exc:
                error_path = project_dir / "logs" / "tts_mux_error.log"
                error_path.parent.mkdir(parents=True, exist_ok=True)
                error_path.write_text(str(exc), encoding="utf-8")
                return TTSResult(
                    enabled=True,
                    audio_path=combined_audio,
                    error=str(exc),
                    status="not_embedded",
                    message="配音文件已生成，但配音未嵌入视频；已保留静音视频。",
                )
        except Exception as exc:
            error_path = project_dir / "logs" / "tts_error.log"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text(str(exc), encoding="utf-8")
            return TTSResult(
                enabled=True,
                status="failed",
                error=str(exc),
                message="配音生成失败，已保留静音视频。",
            )

    def synthesize_project_audio(
        self,
        *,
        scene_narrations: list[str],
        project_dir: Path,
        video_path: Path | None,
    ) -> TTSResult:
        """Synthesize narration with per-scene retries so one network failure does not kill all audio."""

        if not self.is_configured():
            return TTSResult(enabled=False)

        audio_dir = project_dir / "audio"
        logs_dir = project_dir / "logs"
        audio_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        tts_log = logs_dir / "tts_segments.jsonl"
        narration_text = "\n".join(text.strip() for text in scene_narrations if text.strip())
        (audio_dir / "narration_text.txt").write_text(narration_text, encoding="utf-8")

        scene_audio_paths: list[Path] = []
        segment_errors: list[str] = []
        for index, text in enumerate(scene_narrations, start=1):
            clean_text = text.strip()
            if not clean_text:
                continue
            output_path = audio_dir / f"scene_{index:02d}.mp3"
            if output_path.exists() and output_path.stat().st_size > 0:
                scene_audio_paths.append(output_path)
                self._append_tts_log(tts_log, {"scene": index, "status": "cached", "path": str(output_path)})
                continue
            try:
                provider = self._synthesize_text_with_fallback(clean_text, output_path)
                scene_audio_paths.append(output_path)
                self._append_tts_log(tts_log, {"scene": index, "status": "ok", "provider": provider, "path": str(output_path)})
            except Exception as exc:
                error = f"scene_{index:02d}: {exc}"
                segment_errors.append(error)
                self._append_tts_log(tts_log, {"scene": index, "status": "failed", "error": str(exc)})

        if not scene_audio_paths:
            error = "\n".join(segment_errors) if segment_errors else "没有可合成的旁白文本。"
            (logs_dir / "tts_error.log").write_text(error, encoding="utf-8")
            return TTSResult(enabled=True, status="failed", error=error, message="配音生成失败：没有可用音频片段。")

        combined_audio = audio_dir / "narration_combined.mp3"
        try:
            self._concat_audio(scene_audio_paths, combined_audio)
        except Exception as exc:
            error = f"音频片段已生成，但合并失败：{exc}"
            (logs_dir / "tts_error.log").write_text(error, encoding="utf-8")
            return TTSResult(enabled=True, audio_path=scene_audio_paths[0], status="audio_partial", error=error, message="配音片段已部分生成，但合并失败。")

        warning = "\n".join(segment_errors) if segment_errors else None
        if not video_path or not video_path.exists():
            return TTSResult(enabled=True, audio_path=combined_audio, status="audio_only", error=warning, message="配音文件已生成，但没有可嵌入的视频。")

        muxed_video = project_dir / "outputs" / "animation_with_audio.mp4"
        try:
            self._mux_audio_video(video_path, combined_audio, muxed_video)
            return TTSResult(
                enabled=True,
                audio_path=combined_audio,
                muxed_video_path=muxed_video,
                error=warning,
                status="embedded_partial" if warning else "embedded",
                message="配音已部分生成并嵌入视频，部分片段失败。" if warning else "配音已生成并嵌入视频。",
            )
        except Exception as exc:
            error = str(exc)
            (logs_dir / "tts_mux_error.log").write_text(error, encoding="utf-8")
            return TTSResult(enabled=True, audio_path=combined_audio, status="not_embedded", error=error, message="配音文件已生成，但配音未嵌入视频；已保留静音视频。")

    def _synthesize_text_with_fallback(self, text: str, output_path: Path) -> str:
        errors: list[str] = []
        if self._fish_configured():
            for attempt in range(1, 4):
                try:
                    self._synthesize_text_fish(text, output_path)
                    return "fish"
                except Exception as exc:
                    errors.append(f"fish attempt {attempt}: {exc}")
                    time.sleep(0.8 * attempt)
        if self._xunfei_configured():
            try:
                self._synthesize_text_xunfei(text, output_path)
                return "xunfei"
            except Exception as exc:
                errors.append(f"xunfei: {exc}")
        raise RuntimeError("; ".join(errors) or "没有可用的 TTS 服务。")

    def _append_tts_log(self, path: Path, payload: dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _fish_configured(self) -> bool:
        return bool(self.settings.fish_tts_enabled and self.settings.fish_tts_api_key)

    def _xunfei_configured(self) -> bool:
        return bool(
            self.settings.xunfei_tts_enabled
            and self.settings.xunfei_app_id
            and self.settings.xunfei_api_key
            and self.settings.xunfei_api_secret
        )

    def _synthesize_text_fish(self, text: str, output_path: Path) -> None:
        encoded_text = text.encode("utf-8")
        if len(encoded_text) > 7600:
            text = encoded_text[:7600].decode("utf-8", errors="ignore")

        payload = {
            "text": text,
            "reference_id": self.settings.fish_tts_reference_id,
            "temperature": 0.7,
            "top_p": 0.7,
            "prosody": {
                "speed": self.settings.fish_tts_speed,
                "volume": 0,
                "normalize_loudness": True,
            },
            "chunk_length": 300,
            "normalize": True,
            "format": self.settings.fish_tts_format,
            "sample_rate": 44100,
            "mp3_bitrate": 128,
            "latency": "normal",
            "max_new_tokens": 1024,
            "repetition_penalty": 1.2,
            "min_chunk_length": 50,
            "condition_on_previous_chunks": True,
            "early_stop_threshold": 1,
        }
        request = urllib.request.Request(
            self.settings.fish_tts_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.fish_tts_api_key}",
                "Content-Type": "application/json",
                "model": self.settings.fish_tts_model,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                audio = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Fish Audio TTS 返回 HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Fish Audio TTS 请求失败: {exc}") from exc

        if not audio:
            raise RuntimeError("Fish Audio TTS 未返回音频数据。")
        output_path.write_bytes(audio)

    def _synthesize_text_xunfei(self, text: str, output_path: Path) -> None:
        encoded_text = text.encode("utf-8")
        if len(encoded_text) > 7800:
            text = encoded_text[:7800].decode("utf-8", errors="ignore")

        request = {
            "common": {"app_id": self.settings.xunfei_app_id},
            "business": {
                "aue": "lame",
                "sfl": 1,
                "auf": "audio/L16;rate=16000",
                "vcn": self.settings.xunfei_tts_voice,
                "tte": "UTF8",
            },
            "data": {
                "status": 2,
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
            },
        }

        ws = websocket.create_connection(self._build_xunfei_auth_url(), timeout=30)
        chunks: list[bytes] = []
        try:
            ws.send(json.dumps(request, ensure_ascii=False))
            while True:
                response = json.loads(ws.recv())
                code = int(response.get("code", -1))
                if code != 0:
                    message = response.get("message") or response.get("desc") or "讯飞语音合成失败"
                    raise RuntimeError(f"讯飞 TTS 返回错误 code={code}: {message}")
                data = response.get("data") or {}
                audio = data.get("audio")
                if audio:
                    chunks.append(base64.b64decode(audio))
                if int(data.get("status", 0)) == 2:
                    break
        finally:
            ws.close()

        if not chunks:
            raise RuntimeError("讯飞 TTS 未返回音频数据。")
        output_path.write_bytes(b"".join(chunks))

    def _build_xunfei_auth_url(self) -> str:
        parsed = urlparse(self.settings.xunfei_tts_url)
        host = parsed.netloc
        path = parsed.path or "/v2/tts"
        date = format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.settings.xunfei_api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.settings.xunfei_api_key}", '
            'algorithm="hmac-sha256", headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        return f"{self.settings.xunfei_tts_url}?authorization={quote(authorization)}&date={quote(date)}&host={quote(host)}"

    def _concat_audio(self, audio_paths: list[Path], output_path: Path) -> None:
        if len(audio_paths) == 1:
            output_path.write_bytes(audio_paths[0].read_bytes())
            return
        concat_file = output_path.parent / "audio_concat_list.txt"
        concat_file.write_text(
            "\n".join(f"file '{str(path.resolve()).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for path in audio_paths),
            encoding="utf-8",
        )
        command = [
            self._ffmpeg_exe(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file.resolve()),
            "-c:a",
            "libmp3lame",
            "-ar",
            "44100",
            str(output_path.resolve()),
        ]
        self._run_ffmpeg(command)

    def _mux_audio_video(self, video_path: Path, audio_path: Path, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self._ffmpeg_exe(),
            "-y",
            "-i",
            str(video_path.resolve()),
            "-i",
            str(audio_path.resolve()),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path.resolve()),
        ]
        self._run_ffmpeg(command)

    def _run_ffmpeg(self, command: list[str]) -> None:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "ffmpeg 执行失败。")

    def _ffmpeg_exe(self) -> str:
        found = shutil.which("ffmpeg")
        if found:
            return found
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            raise RuntimeError("找不到 ffmpeg。请安装 ffmpeg，或安装 imageio-ffmpeg。") from exc
