from __future__ import annotations

import ast
import configparser
import io
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image

from backend.workflow.templates import math_function_template


ANIMATIONS = {
    "Create", "Write", "FadeIn", "FadeOut", "Transform", "ReplacementTransform",
    "TransformFromCopy", "TransformMatchingShapes", "TransformMatchingTex",
    "GrowFromCenter", "DrawBorderThenFill", "AnimationGroup", "LaggedStart",
    "Succession", "Uncreate", "Circumscribe", "Indicate",
}
MOBJECTS = {
    "Text", "MarkupText", "Paragraph", "MathTex", "Tex", "VGroup", "Group",
    "Circle", "Square", "Rectangle", "RoundedRectangle", "Triangle", "Polygon",
    "Line", "Arrow", "Vector", "Dot", "Axes", "NumberPlane", "NumberLine",
    "ImageMobject", "SVGMobject", "Table", "Matrix", "ValueTracker",
}
LAYOUT_METHODS = {"arrange", "arrange_in_grid", "next_to", "align_to", "to_edge", "to_corner", "move_to", "shift"}
CAMERA_METHODS = {
    "set_camera_orientation", "move_camera", "begin_ambient_camera_rotation",
    "stop_ambient_camera_rotation", "auto_zoom",
}
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}|(?:BLUE|RED|GREEN|YELLOW|ORANGE|PURPLE|TEAL|GOLD|MAROON|GREY|GRAY|WHITE|BLACK)(?:_[A-E])?")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _literal_number(node: ast.AST | None, default: float) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    return default


class ManimCodeAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scenes: list[dict[str, Any]] = []
        self.functions: Counter[str] = Counter()
        self.objects: Counter[str] = Counter()
        self.animations: Counter[str] = Counter()
        self.layouts: Counter[str] = Counter()
        self.colors: Counter[str] = Counter()
        self.fonts: Counter[str] = Counter()
        self.font_sizes: list[float] = []
        self.play_durations: list[float] = []
        self.wait_durations: list[float] = []
        self.camera: Counter[str] = Counter()
        self.current_scene: dict[str, Any] | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [self._expr_name(base) for base in node.bases]
        scene_base = next((name for name in bases if name.endswith("Scene")), "")
        previous = self.current_scene
        if scene_base:
            self.current_scene = {
                "name": node.name,
                "type": scene_base,
                "methods": [item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))],
                "objects": [],
                "animations": [],
            }
            self.scenes.append(self.current_scene)
        self.generic_visit(node)
        self.current_scene = previous

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name not in {"construct", "setup"}:
            self.functions[node.name] += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name in MOBJECTS:
            self.objects[name] += 1
            if self.current_scene is not None:
                self.current_scene["objects"].append(name)
        if name in ANIMATIONS:
            self.animations[name] += 1
            if self.current_scene is not None:
                self.current_scene["animations"].append(name)
        if name in LAYOUT_METHODS:
            self.layouts[name] += 1
        if name in CAMERA_METHODS:
            self.camera[name] += 1
        if name == "play":
            duration = next((_literal_number(kw.value, 1.0) for kw in node.keywords if kw.arg == "run_time"), 1.0)
            self.play_durations.append(duration)
        if name == "wait":
            self.wait_durations.append(_literal_number(node.args[0] if node.args else None, 1.0))
        for keyword in node.keywords:
            if keyword.arg == "font" and isinstance(keyword.value, ast.Constant):
                self.fonts[str(keyword.value.value)] += 1
            if keyword.arg == "font_size":
                value = _literal_number(keyword.value, 0)
                if value:
                    self.font_sizes.append(value)
        self.generic_visit(node)

    @staticmethod
    def _expr_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""


class StyleLibraryService:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "styles.json"
        if not self.index_path.exists():
            self._write({"version": 1, "styles": []})

    def list_styles(self) -> dict[str, Any]:
        return self._read()

    def get_style(self, style_id: str, version: int | None = None) -> dict[str, Any]:
        style = next((item for item in self._read()["styles"] if item["id"] == style_id), None)
        if not style:
            raise ValueError("找不到风格预设。")
        if version is None:
            return style
        match = next((item for item in style["versions"] if item["version"] == version), None)
        if not match:
            raise ValueError("找不到指定版本。")
        return {**style, "active_version": version, "preset": match["preset"], "analysis": match["analysis"]}

    def analyze(
        self,
        *,
        style_name: str,
        files: list[tuple[str, bytes]],
        existing_style_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        python_files = [(name, data) for name, data in files if name.lower().endswith(".py")]
        if not python_files:
            raise ValueError("至少需要一个 Manim Python 源文件。")
        analysis = self._analyze_files(files)
        preset = self._build_preset(style_name, description, analysis)
        data = self._read()
        existing = next((item for item in data["styles"] if item["id"] == existing_style_id), None)
        version = len(existing["versions"]) + 1 if existing else 1
        changes = self._diff_analysis(existing.get("analysis", {}), analysis) if existing else {"summary": ["初始版本"]}
        record = {"version": version, "created_at": _now(), "analysis": analysis, "preset": preset, "changes": changes}
        if existing:
            existing["name"] = style_name or existing["name"]
            existing["description"] = description or preset["style_description"]
            existing["updated_at"] = _now()
            existing["active_version"] = version
            existing["versions"].append(record)
            existing["preset"] = preset
            existing["analysis"] = analysis
            style = existing
        else:
            style = {
                "id": f"style-{uuid4().hex[:12]}",
                "name": style_name or "未命名 Manim 风格",
                "description": description or preset["style_description"],
                "created_at": _now(),
                "updated_at": _now(),
                "active_version": 1,
                "versions": [record],
                "preset": preset,
                "analysis": analysis,
            }
            data["styles"].append(style)
        self._write(data)
        return style

    def save_preset(self, style_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        style = next((item for item in data["styles"] if item["id"] == style_id), None)
        if not style:
            raise ValueError("找不到风格预设。")
        preset = {**style["preset"], **payload}
        version = len(style["versions"]) + 1
        record = {"version": version, "created_at": _now(), "analysis": style["analysis"], "preset": preset}
        style.update(
            name=str(payload.get("name") or style["name"]),
            description=str(payload.get("style_description") or style["description"]),
            updated_at=_now(),
            active_version=version,
            preset=preset,
        )
        style["versions"].append(record)
        self._write(data)
        return style

    def apply_model_analysis(self, style_id: str, result: dict[str, Any], model_name: str) -> dict[str, Any]:
        """Merge one model call into the version created by the same learning run."""

        data = self._read()
        style = next((item for item in data["styles"] if item["id"] == style_id), None)
        if not style:
            raise ValueError("找不到风格预设。")
        preset = style["preset"]
        preset.update(
            name=str(result.get("style_name") or preset["name"]),
            style_description=str(result.get("style_description") or preset["style_description"]),
            prompt_preset=str(result.get("prompt_preset") or preset["prompt_preset"]),
            scene_count=max(1, int(result.get("recommended_scene_count") or preset["scene_count"])),
            animation_speed=str(result.get("animation_speed") or preset["animation_speed"]),
            palette=list(result.get("palette") or preset["palette"]),
            fonts=list(result.get("fonts") or preset["fonts"]),
        )
        style["name"] = preset["name"]
        style["description"] = preset["style_description"]
        style["analysis"]["model_analysis"] = {
            "status": "success",
            "model": model_name,
            "visual_style": result.get("visual_style", {}),
            "teaching_rhythm": result.get("teaching_rhythm", {}),
            "code_patterns": result.get("code_patterns", {}),
            "confidence": result.get("confidence"),
            "inference_notes": result.get("inference_notes", []),
        }
        style["analysis"]["analysis_method"] = "local-evidence+model-api"
        style["versions"][-1]["analysis"] = style["analysis"]
        style["versions"][-1]["preset"] = preset
        style["updated_at"] = _now()
        self._write(data)
        return style

    def mark_model_fallback(self, style_id: str, message: str, model_name: str = "") -> dict[str, Any]:
        data = self._read()
        style = next((item for item in data["styles"] if item["id"] == style_id), None)
        if not style:
            raise ValueError("找不到风格预设。")
        style["analysis"]["model_analysis"] = {"status": "fallback", "model": model_name, "message": message}
        style["analysis"]["analysis_method"] = "local-fallback"
        style["versions"][-1]["analysis"] = style["analysis"]
        self._write(data)
        return style

    def rollback(self, style_id: str, version: int) -> dict[str, Any]:
        data = self._read()
        style = next((item for item in data["styles"] if item["id"] == style_id), None)
        if not style:
            raise ValueError("找不到风格预设。")
        record = next((item for item in style["versions"] if item["version"] == version), None)
        if not record:
            raise ValueError("找不到指定版本。")
        style["active_version"] = version
        style["preset"] = record["preset"]
        style["analysis"] = record["analysis"]
        style["updated_at"] = _now()
        self._write(data)
        return style

    def import_style(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or payload.get("preset", {}).get("name") or "导入风格")
        preset = dict(payload.get("preset") or payload)
        analysis = dict(payload.get("analysis") or {})
        data = self._read()
        now = _now()
        style = {
            "id": f"style-{uuid4().hex[:12]}",
            "name": name,
            "description": str(payload.get("description") or preset.get("style_description") or ""),
            "created_at": now,
            "updated_at": now,
            "active_version": 1,
            "versions": [{"version": 1, "created_at": now, "analysis": analysis, "preset": preset}],
            "preset": preset,
            "analysis": analysis,
        }
        data["styles"].append(style)
        self._write(data)
        return style

    def _analyze_files(self, files: list[tuple[str, bytes]]) -> dict[str, Any]:
        aggregate = ManimCodeAnalyzer()
        source_samples: list[str] = []
        framework_signals: Counter[str] = Counter()
        parse_errors: list[str] = []
        storyboard_text = ""
        media: list[dict[str, Any]] = []
        cfg: dict[str, str] = {}
        for name, data in files:
            suffix = Path(name).suffix.lower()
            if suffix == ".py":
                source = data.decode("utf-8", errors="replace")
                source_samples.append(source[:3000])
                if re.search(r"^\s*(?:from|import)\s+manimlib\b", source, re.MULTILINE):
                    framework_signals["ManimGL"] += 1
                if re.search(r"^\s*(?:from|import)\s+manim\b", source, re.MULTILINE):
                    framework_signals["ManimCE"] += 1
                aggregate.colors.update(COLOR_RE.findall(source))
                try:
                    aggregate.visit(ast.parse(source, filename=name))
                except SyntaxError as exc:
                    parse_errors.append(f"{name}:{exc.lineno} {exc.msg}")
            elif suffix in {".json", ".srt", ".vtt", ".md", ".txt"}:
                storyboard_text += "\n" + data.decode("utf-8", errors="replace")[:30000]
            elif name.lower().endswith("manim.cfg"):
                parser = configparser.ConfigParser()
                parser.read_string(data.decode("utf-8", errors="replace"))
                cfg = {f"{section}.{key}": value for section in parser.sections() for key, value in parser[section].items()}
            elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                media.append(self._image_evidence(name, data))
            elif suffix in {".mp4", ".mov", ".webm"}:
                media.append(self._av_evidence(name, data, sample_frames=True))
            elif suffix in {".mp3", ".wav", ".m4a"}:
                media.append(self._av_evidence(name, data, sample_frames=False))

        total_play = sum(aggregate.play_durations)
        total_wait = sum(aggregate.wait_durations)
        average_play = total_play / len(aggregate.play_durations) if aggregate.play_durations else 1.0
        reveal_count = sum(aggregate.animations[name] for name in ("Create", "Write", "FadeIn"))
        transform_count = sum(aggregate.animations[name] for name in ("Transform", "ReplacementTransform", "TransformMatchingShapes", "TransformMatchingTex"))
        visual_label = self._classify_visual(aggregate)
        cadence = "快速" if average_play < 0.9 else "舒缓" if average_play > 1.8 else "中等"
        confidence = min(0.98, 0.45 + 0.04 * len(aggregate.scenes) + (0.18 if any(item.get("palette") for item in media) else 0))
        return {
            "framework": framework_signals.most_common(1)[0][0] if framework_signals else "unknown",
            "files_analyzed": len(files),
            "parse_errors": parse_errors,
            "code_structure": {
                "scene_count": len(aggregate.scenes),
                "scenes": aggregate.scenes,
                "custom_functions": dict(aggregate.functions.most_common()),
                "objects": dict(aggregate.objects.most_common()),
                "animations": dict(aggregate.animations.most_common()),
                "layouts": dict(aggregate.layouts.most_common()),
                "camera": dict(aggregate.camera.most_common()),
            },
            "visual_style": {
                "classification": visual_label,
                "background": cfg.get("renderer.background_color") or aggregate.colors.most_common(1)[0][0] if aggregate.colors else "BLACK",
                "palette": [name for name, _ in aggregate.colors.most_common(8)],
                "fonts": [name for name, _ in aggregate.fonts.most_common(5)],
                "font_size_range": [min(aggregate.font_sizes), max(aggregate.font_sizes)] if aggregate.font_sizes else [],
                "layout_patterns": [name for name, _ in aggregate.layouts.most_common(6)],
                "media_evidence": media,
            },
            "teaching_rhythm": {
                "cadence": cadence,
                "estimated_duration_seconds": round(total_play + total_wait, 2),
                "average_animation_seconds": round(average_play, 2),
                "average_wait_seconds": round(total_wait / len(aggregate.wait_durations), 2) if aggregate.wait_durations else 0,
                "reveal_count": reveal_count,
                "transform_count": transform_count,
                "mode": "逐步揭示" if reveal_count >= transform_count else "变换推导",
                "storyboard_or_subtitle_chars": len(storyboard_text.strip()),
            },
            "confidence": round(confidence, 2),
            "example_code": "\n\n".join(source_samples)[:6000],
        }

    @staticmethod
    def _image_evidence(name: str, data: bytes) -> dict[str, Any]:
        try:
            image = Image.open(io.BytesIO(data)).convert("RGB")
            image.thumbnail((160, 90))
            colors = Counter(image.getdata()).most_common(6)
            return {"name": name, "type": "image", "size": list(image.size), "palette": [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in colors]}
        except Exception as exc:
            return {"name": name, "type": "image", "error": str(exc)}

    @classmethod
    def _av_evidence(cls, name: str, data: bytes, *, sample_frames: bool) -> dict[str, Any]:
        evidence: dict[str, Any] = {
            "name": name,
            "type": Path(name).suffix.lower()[1:],
            "bytes": len(data),
            "analyzed": "metadata-only",
        }
        ffprobe = shutil.which("ffprobe")
        ffmpeg = shutil.which("ffmpeg")
        if not ffprobe:
            return evidence
        with tempfile.TemporaryDirectory(prefix="manim-style-") as temp_dir:
            source = Path(temp_dir) / f"source{Path(name).suffix.lower()}"
            source.write_bytes(data)
            try:
                probe = subprocess.run(
                    [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(source)],
                    capture_output=True, text=True, timeout=20, check=True,
                )
                evidence["duration_seconds"] = round(float(probe.stdout.strip()), 2)
                evidence["analyzed"] = "duration"
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            if sample_frames and ffmpeg:
                frame_pattern = str(Path(temp_dir) / "frame-%02d.jpg")
                try:
                    subprocess.run(
                        [ffmpeg, "-v", "error", "-i", str(source), "-vf", "fps=1/5,scale=320:-1", "-frames:v", "6", frame_pattern],
                        capture_output=True, timeout=45, check=True,
                    )
                    frames = sorted(Path(temp_dir).glob("frame-*.jpg"))
                    palettes = [cls._image_evidence(frame.name, frame.read_bytes()).get("palette", []) for frame in frames]
                    evidence["sampled_frames"] = len(frames)
                    evidence["frame_palettes"] = palettes
                    evidence["palette"] = [color for color, _ in Counter(color for palette in palettes for color in palette).most_common(8)]
                    evidence["analyzed"] = "sampled-frames"
                except (OSError, subprocess.SubprocessError):
                    pass
        return evidence

    @staticmethod
    def _classify_visual(analyzer: ManimCodeAnalyzer) -> str:
        if analyzer.objects["MathTex"] + analyzer.objects["Tex"] >= 4 and analyzer.animations["TransformMatchingTex"] + analyzer.animations["ReplacementTransform"] >= 2:
            return "数学推导 / 3Blue1Brown"
        if analyzer.objects["RoundedRectangle"] + analyzer.objects["Rectangle"] >= 5:
            return "卡片式信息图"
        if analyzer.objects["Text"] >= 6 and analyzer.animations["FadeIn"] >= analyzer.animations["Create"]:
            return "PPT 教学"
        if analyzer.camera:
            return "镜头叙事型"
        return "极简 Manim 教学"

    @staticmethod
    def _build_preset(name: str, description: str, analysis: dict[str, Any]) -> dict[str, Any]:
        visual = analysis["visual_style"]
        rhythm = analysis["teaching_rhythm"]
        structure = analysis["code_structure"]
        framework = analysis.get("framework", "ManimCE")
        scene_count = max(1, structure["scene_count"])
        prompt = (
            f"请严格复用“{name}”的 {framework} 生成风格；若目标运行时为 ManimCE，则只迁移视觉与节奏规律并使用 ManimCE API。\n"
            f"视觉：{visual['classification']}；背景 {visual['background']}；主色 {', '.join(visual['palette']) or '从参考工程提取'}；"
            f"布局优先使用 {', '.join(visual['layout_patterns']) or 'VGroup、arrange、next_to'}。\n"
            f"结构：约 {scene_count} 个 Scene；常用对象 {', '.join(list(structure['objects'])[:8])}；"
            f"常用动画 {', '.join(list(structure['animations'])[:8])}。\n"
            f"节奏：{rhythm['cadence']}，单段动画约 {rhythm['average_animation_seconds']} 秒，采用{rhythm['mode']}；"
            "保持概念颜色映射一致、留白稳定、禁止无意义装饰和大面积空场。"
        )
        workflow = math_function_template().model_dump()
        workflow["workflow_name"] = f"{name} 工作流"
        workflow["description"] = description or f"由已有 Manim 工程自动学习得到的 {visual['classification']} 风格。"
        workflow["template_info"] = {"builtin": False, "style_library": True, "style_name": name}
        for node in workflow["nodes"]:
            if node["id"] == "prompt":
                node["params"]["style_preset"] = prompt
            if node["id"] in {"plan", "storyboard", "code"}:
                node["params"]["style_preset"] = prompt
        return {
            "name": name,
            "style_description": description or workflow["description"],
            "prompt_preset": prompt,
            "scene_count": scene_count,
            "animation_speed": rhythm["cadence"],
            "palette": visual["palette"],
            "fonts": visual["fonts"],
            "workflow": workflow,
            "example_code": analysis.get("example_code", ""),
        }

    @staticmethod
    def _diff_analysis(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        def keys(path: str) -> set[str]:
            old = previous.get("code_structure", {}).get(path, {})
            new = current.get("code_structure", {}).get(path, {})
            return set(old) | set(new)

        changes: dict[str, Any] = {"added": {}, "removed": {}, "changed": {}, "summary": []}
        for category in ("objects", "animations", "layouts", "camera"):
            old = previous.get("code_structure", {}).get(category, {})
            new = current.get("code_structure", {}).get(category, {})
            changes["added"][category] = sorted(name for name in keys(category) if name not in old and name in new)
            changes["removed"][category] = sorted(name for name in keys(category) if name in old and name not in new)
            changes["changed"][category] = {
                name: {"from": old[name], "to": new[name]}
                for name in keys(category)
                if name in old and name in new and old[name] != new[name]
            }
        old_scenes = previous.get("code_structure", {}).get("scene_count", 0)
        new_scenes = current.get("code_structure", {}).get("scene_count", 0)
        if old_scenes != new_scenes:
            changes["summary"].append(f"Scene 数量从 {old_scenes} 调整为 {new_scenes}")
        old_class = previous.get("visual_style", {}).get("classification")
        new_class = current.get("visual_style", {}).get("classification")
        if old_class != new_class:
            changes["summary"].append(f"视觉分类从 {old_class or '未知'} 调整为 {new_class or '未知'}")
        old_cadence = previous.get("teaching_rhythm", {}).get("cadence")
        new_cadence = current.get("teaching_rhythm", {}).get("cadence")
        if old_cadence != new_cadence:
            changes["summary"].append(f"教学节奏从 {old_cadence or '未知'} 调整为 {new_cadence or '未知'}")
        if not changes["summary"]:
            changes["summary"].append("核心风格结构保持稳定，已更新统计与证据")
        return changes

    def _read(self) -> dict[str, Any]:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        temp = self.index_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.index_path)
