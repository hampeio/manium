from pathlib import Path

from PIL import Image


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def validate_image(image_path: Path) -> dict[str, str | int]:
    """Validate image format and return basic metadata."""

    if image_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")
    with Image.open(image_path) as image:
        image.verify()
    with Image.open(image_path) as image:
        return {"format": image.format or image_path.suffix.lower().lstrip("."), "width": image.width, "height": image.height}


def transcode_or_compress_placeholder(image_path: Path) -> Path:
    """Reserved hook for v2 compression/transcoding nodes."""

    return image_path
