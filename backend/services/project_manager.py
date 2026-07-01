import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class ProjectManager:
    """Creates isolated project folders and writes task artifacts."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create_project(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = self.root / f"{timestamp}_{uuid4().hex[:8]}"
        project_dir.mkdir(parents=True, exist_ok=False)
        (project_dir / "inputs").mkdir()
        (project_dir / "outputs").mkdir()
        (project_dir / "logs").mkdir()
        (project_dir / "repairs").mkdir()
        return project_dir

    async def save_upload(self, project_dir: Path, upload: UploadFile | None) -> Path | None:
        if not upload or not upload.filename:
            return None
        suffix = Path(upload.filename).suffix.lower()
        target = project_dir / "inputs" / f"uploaded_image{suffix}"
        with target.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                handle.write(chunk)
        return target

    def write_text(self, project_dir: Path, relative_path: str, content: str) -> Path:
        path = project_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_json(self, project_dir: Path, relative_path: str, data: object) -> Path:
        return self.write_text(project_dir, relative_path, json.dumps(data, ensure_ascii=False, indent=2))

    def copy_video_to_output(self, project_dir: Path, video_path: Path) -> Path:
        target = project_dir / "outputs" / "animation.mp4"
        shutil.copy2(video_path, target)
        return target
