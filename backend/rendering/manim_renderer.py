import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path


QUALITY_FLAGS = {
    "preview_720p": ["-qm"],
    "final_1080p": ["-qh"],
    "low": ["-ql"],
}


@dataclass
class RenderResult:
    success: bool
    stdout: str
    stderr: str
    video_path: Path | None
    command: list[str]
    environment_error: bool = False


class ManimRenderer:
    """Runs Manim in a project-local media directory and captures logs."""

    def __init__(self, manim_command: str):
        parts = manim_command.split()
        if len(parts) >= 3 and parts[0].lower() == "python" and parts[1:3] == ["-m", "manim"]:
            parts[0] = sys.executable
        self.command_parts = parts

    async def render(self, scene_file: Path, scene_name: str, media_dir: Path, quality: str) -> RenderResult:
        media_dir.mkdir(parents=True, exist_ok=True)
        command = [
            *self.command_parts,
            *QUALITY_FLAGS.get(quality, QUALITY_FLAGS["preview_720p"]),
            "--media_dir",
            str(media_dir.resolve()),
            str(scene_file.resolve()),
            scene_name,
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(scene_file.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        video_path = self._find_latest_mp4(media_dir)
        environment_error = self._is_environment_error(stdout + "\n" + stderr)
        return RenderResult(process.returncode == 0 and video_path is not None, stdout, stderr, video_path, command, environment_error)

    def save_log(self, path: Path, result: RenderResult) -> None:
        payload = {
            "success": result.success,
            "command": result.command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "video_path": str(result.video_path) if result.video_path else None,
            "environment_error": result.environment_error,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _find_latest_mp4(self, media_dir: Path) -> Path | None:
        files = sorted(media_dir.rglob("*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True)
        return files[0] if files else None

    def _is_environment_error(self, output: str) -> bool:
        markers = [
            "No module named manim",
            "manim is not recognized",
            "No module named 'manim'",
            "ffmpeg",
        ]
        return any(marker.lower() in output.lower() for marker in markers)
