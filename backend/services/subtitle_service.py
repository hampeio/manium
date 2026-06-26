from backend.ai.schemas import StoryboardScene


def build_subtitles(scenes: list[StoryboardScene]) -> tuple[str, list[dict[str, object]]]:
    """Build SRT text and a JSON-friendly timeline from storyboard narration."""

    entries: list[dict[str, object]] = []
    cursor = 0.0
    srt_blocks: list[str] = []
    for scene in scenes:
        start = cursor
        end = cursor + max(scene.estimated_seconds, 3)
        entries.append({"index": scene.index, "start": start, "end": end, "text": scene.narration, "title": scene.title})
        srt_blocks.append(f"{scene.index}\n{_srt_time(start)} --> {_srt_time(end)}\n{scene.narration}\n")
        cursor = end
    return "\n".join(srt_blocks), entries


def _srt_time(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02}:{m:02}:{s:02},{millis:03}"
