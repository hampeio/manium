from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ImageNode(ABC):
    """Base interface reserved for future OCR, detection, segmentation, and markup nodes."""

    name: str

    @abstractmethod
    def run(self, image_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        """Process an image and return updated context."""
