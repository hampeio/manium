from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a Manim project and export a reusable style preset.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--name", default="自动学习风格")
    parser.add_argument("--description", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo))
    from backend.services.style_library_service import StyleLibraryService

    source = args.source.resolve()
    if not source.exists():
        parser.error(f"source does not exist: {source}")
    paths = [source] if source.is_file() else [
        item for item in source.rglob("*")
        if item.is_file() and item.suffix.lower() in {
            ".py", ".json", ".srt", ".vtt", ".md", ".txt", ".cfg",
            ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".mp4", ".mov",
            ".webm", ".mp3", ".wav", ".m4a",
        }
    ]
    files = [(str(item.relative_to(source.parent if source.is_file() else source)), item.read_bytes()) for item in paths]
    service = StyleLibraryService(args.output.parent / ".style-library-work")
    analysis = service._analyze_files(files)
    preset = service._build_preset(args.name, args.description, analysis)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"analysis": analysis, "preset": preset}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
