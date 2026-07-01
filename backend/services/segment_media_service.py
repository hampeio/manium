import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from backend.services.tts_service import TTSService


class SegmentMediaService:
    """Builds versioned, duration-aligned media assets for one timeline segment."""

    tolerance_seconds = 0.08

    def __init__(self, tts_service: TTSService):
        self.tts_service = tts_service

    def prepare_segment(
        self,
        *,
        project_dir: Path,
        segment_id: str,
        rendered_video: Path,
        narration_text: str,
        revision: int,
        previous: dict[str, object] | None = None,
    ) -> dict[str, object]:
        safe_id = self._safe_id(segment_id)
        video_dir = project_dir / "outputs" / "segments"
        audio_dir = project_dir / "outputs" / "audio"
        subtitle_dir = project_dir / "outputs" / "subtitles"
        preview_dir = project_dir / "outputs" / "previews"
        for folder in (video_dir, audio_dir, subtitle_dir, preview_dir):
            folder.mkdir(parents=True, exist_ok=True)

        video_path = video_dir / f"{safe_id}_v{revision:03d}.mp4"
        shutil.copy2(rendered_video, video_path)
        video_duration = self.probe_duration(video_path)
        if video_duration <= 0:
            raise RuntimeError(f"Cannot determine video duration for {segment_id}.")

        source_audio = self._source_audio(
            audio_dir=audio_dir,
            safe_id=safe_id,
            revision=revision,
            narration_text=narration_text,
            previous=previous,
        )
        audio_path = audio_dir / f"{safe_id}_v{revision:03d}.wav"
        timing_adjustment = "none"
        if source_audio and source_audio.exists():
            audio_duration = self.probe_duration(source_audio)
            if audio_duration > video_duration + self.tolerance_seconds:
                self._extend_video(video_path, audio_duration - video_duration)
                video_duration = self.probe_duration(video_path)
                timing_adjustment = "video_extended_to_audio"
            elif audio_duration < video_duration - self.tolerance_seconds:
                timing_adjustment = "audio_padded_to_video"
            final_duration = max(video_duration, audio_duration)
            self._normalize_audio(source_audio, audio_path, final_duration)
        else:
            final_duration = video_duration
            self._create_silence(audio_path, final_duration)
            timing_adjustment = "silent_audio_created"

        final_video_duration = self.probe_duration(video_path)
        final_audio_duration = self.probe_duration(audio_path)
        final_duration = max(final_video_duration, final_audio_duration)
        if final_video_duration < final_duration - self.tolerance_seconds:
            self._extend_video(video_path, final_duration - final_video_duration)
        if final_audio_duration < final_duration - self.tolerance_seconds:
            self._normalize_audio(audio_path, audio_path.with_suffix(".aligned.wav"), final_duration)
            audio_path.with_suffix(".aligned.wav").replace(audio_path)

        subtitle_path = subtitle_dir / f"{safe_id}_v{revision:03d}.srt"
        subtitle_path.write_text(self._segment_srt(narration_text, final_duration), encoding="utf-8")
        preview_path = preview_dir / f"{safe_id}_v{revision:03d}.mp4"
        self._mux_preview(video_path, audio_path, preview_path, final_duration)
        now = datetime.now(timezone.utc).isoformat()
        original_video = (previous or {}).get("original_video_path") or str(video_path.resolve())
        original_preview = (previous or {}).get("original_preview_path") or str(preview_path.resolve())
        history = list((previous or {}).get("revision_history") or [])
        if previous:
            history.append(
                {
                    "revision": previous.get("revision", 1),
                    "video_path": previous.get("video_path"),
                    "audio_path": previous.get("audio_path"),
                    "subtitle_path": previous.get("subtitle_path"),
                    "preview_video_path": previous.get("preview_video_path"),
                    "duration": previous.get("duration"),
                    "updated_at": previous.get("updated_at"),
                }
            )
        return {
            "video_path": str(video_path.resolve()),
            "audio_path": str(audio_path.resolve()),
            "audio_source_path": str(source_audio.resolve()) if source_audio else None,
            "subtitle_path": str(subtitle_path.resolve()),
            "preview_video_path": str(preview_path.resolve()),
            "original_video_path": original_video,
            "original_preview_path": original_preview,
            "corrected_video_path": str(video_path.resolve()) if revision > 1 else None,
            "corrected_preview_path": str(preview_path.resolve()) if revision > 1 else None,
            "duration": round(final_duration, 3),
            "narration_text": narration_text,
            "revision": revision,
            "revision_history": history,
            "timing_adjustment": timing_adjustment,
            "updated_at": now,
        }

    def synchronize_timeline(self, project_dir: Path, segments: list[dict[str, object]]) -> list[dict[str, object]]:
        cursor = 0.0
        timeline: list[dict[str, object]] = []
        srt_blocks: list[str] = []
        for index, segment in enumerate(segments, start=1):
            duration = max(0.0, float(segment.get("duration") or segment.get("estimated_seconds") or 0.0))
            start = cursor
            end = start + duration
            segment["start_time"] = round(start, 3)
            segment["end_time"] = round(end, 3)
            narration = str(segment.get("narration_text") or segment.get("narration") or "")
            timeline.append(
                {
                    "index": index,
                    "segment_id": segment.get("id"),
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": narration,
                    "title": segment.get("title"),
                }
            )
            if narration:
                srt_blocks.append(f"{index}\n{self._srt_time(start)} --> {self._srt_time(end)}\n{narration}\n")
            cursor = end
        (project_dir / "timeline_subtitles.json").write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (project_dir / "subtitles.srt").write_text("\n".join(srt_blocks), encoding="utf-8")
        (project_dir / "timeline_manifest.json").write_text(
            json.dumps(
                {"version": 1, "duration": round(cursor, 3), "segments": timeline},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return segments

    def compose_project(self, project_dir: Path, segments: list[dict[str, object]]) -> dict[str, object]:
        if not segments:
            raise ValueError("No timeline segments are available for composition.")
        compose_dir = project_dir / "outputs" / "final"
        parts_dir = compose_dir / "parts"
        if parts_dir.exists():
            shutil.rmtree(parts_dir)
        parts_dir.mkdir(parents=True, exist_ok=True)

        video_parts: list[Path] = []
        audio_parts: list[Path] = []
        total_duration = 0.0
        for index, segment in enumerate(segments, start=1):
            source_video = Path(str(segment.get("video_path") or ""))
            if not source_video.exists():
                raise FileNotFoundError(f"Missing video for segment {segment.get('id')}.")
            source_audio = Path(str(segment.get("audio_path") or ""))
            expected = max(0.01, float(segment.get("duration") or self.probe_duration(source_video)))
            video_part = parts_dir / f"video_{index:03d}.mp4"
            audio_part = parts_dir / f"audio_{index:03d}.wav"
            shutil.copy2(source_video, video_part)
            video_duration = self.probe_duration(video_part)
            if source_audio.exists():
                audio_duration = self.probe_duration(source_audio)
                final_duration = max(expected, video_duration, audio_duration)
                if video_duration < final_duration - self.tolerance_seconds:
                    self._extend_video(video_part, final_duration - video_duration)
                self._normalize_audio(source_audio, audio_part, final_duration)
            else:
                final_duration = max(expected, video_duration)
                if video_duration < final_duration - self.tolerance_seconds:
                    self._extend_video(video_part, final_duration - video_duration)
                self._create_silence(audio_part, final_duration)
            video_parts.append(video_part)
            audio_parts.append(audio_part)
            total_duration += final_duration

        combined_video = compose_dir / "combined_video.mp4"
        combined_audio = compose_dir / "combined_audio.wav"
        self._concat(video_parts, compose_dir / "video_concat.txt", combined_video, ["-c", "copy"])
        self._concat(audio_parts, compose_dir / "audio_concat.txt", combined_audio, ["-c:a", "pcm_s16le"])
        final_video = compose_dir / "course_final.mp4"
        self._run(
            [
                self._ffmpeg_exe(), "-y", "-i", str(combined_video), "-i", str(combined_audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                "-t", f"{total_duration:.3f}", str(final_video),
            ]
        )
        return {
            "video_path": str(final_video.resolve()),
            "combined_video_path": str(combined_video.resolve()),
            "combined_audio_path": str(combined_audio.resolve()),
            "duration": round(total_duration, 3),
            "composed_at": datetime.now(timezone.utc).isoformat(),
        }

    def probe_duration(self, path: Path) -> float:
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            completed = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            try:
                return max(0.0, float(completed.stdout.strip()))
            except ValueError:
                pass
        completed = subprocess.run(
            [self._ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stderr)
        if not match:
            return 0.0
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))

    def _source_audio(
        self,
        *,
        audio_dir: Path,
        safe_id: str,
        revision: int,
        narration_text: str,
        previous: dict[str, object] | None,
    ) -> Path | None:
        previous_source = Path(str((previous or {}).get("audio_source_path") or ""))
        previous_text = str((previous or {}).get("narration_text") or (previous or {}).get("narration") or "")
        if previous_source.exists() and previous_text == narration_text:
            return previous_source
        if not self.tts_service.is_configured() or not narration_text.strip():
            return None
        source = audio_dir / f"{safe_id}_v{revision:03d}_source.mp3"
        result = self.tts_service.synthesize_segment_audio(narration_text, source)
        if not result.audio_path:
            raise RuntimeError(result.error or "Segment narration synthesis failed.")
        return result.audio_path

    def _normalize_audio(self, source: Path, output: Path, duration: float) -> None:
        self._run(
            [
                self._ffmpeg_exe(), "-y", "-i", str(source), "-af", "apad",
                "-t", f"{duration:.3f}", "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(output),
            ]
        )

    def _extend_video(self, video_path: Path, extension: float) -> None:
        temporary = video_path.with_name(f"{video_path.stem}.extended.mp4")
        self._run(
            [
                self._ffmpeg_exe(), "-y", "-i", str(video_path),
                "-vf", f"tpad=stop_mode=clone:stop_duration={max(0.0, extension):.3f}",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(temporary),
            ]
        )
        temporary.replace(video_path)

    def _create_silence(self, output: Path, duration: float) -> None:
        self._run(
            [
                self._ffmpeg_exe(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", f"{duration:.3f}", "-c:a", "pcm_s16le", str(output),
            ]
        )

    def _mux_preview(self, video: Path, audio: Path, output: Path, duration: float) -> None:
        self._run(
            [
                self._ffmpeg_exe(), "-y", "-i", str(video), "-i", str(audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                "-t", f"{duration:.3f}", str(output),
            ]
        )

    def _concat(self, paths: list[Path], list_path: Path, output: Path, codec_args: list[str]) -> None:
        list_path.write_text("\n".join(f"file '{path.as_posix()}'" for path in paths), encoding="utf-8")
        self._run([self._ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), *codec_args, str(output)])

    def _run(self, command: list[str]) -> None:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "ffmpeg command failed.")

    def _ffmpeg_exe(self) -> str:
        found = shutil.which("ffmpeg")
        if found:
            return found
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            raise RuntimeError("ffmpeg is required for segment media synchronization.") from exc

    @staticmethod
    def _safe_id(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "segment"

    @classmethod
    def _segment_srt(cls, text: str, duration: float) -> str:
        return f"1\n{cls._srt_time(0)} --> {cls._srt_time(duration)}\n{text}\n" if text else ""

    @staticmethod
    def _srt_time(seconds: float) -> str:
        millis_total = max(0, round(seconds * 1000))
        hours, remainder = divmod(millis_total, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, millis = divmod(remainder, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
