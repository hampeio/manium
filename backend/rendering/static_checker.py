import py_compile
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class StaticCheckResult:
    """Result of a local syntax-only guard before expensive Manim rendering."""

    success: bool
    error: str
    checked_path: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_static_check(scene_file: Path) -> StaticCheckResult:
    """Compiles generated Python and optionally runs mypy when available."""

    try:
        py_compile.compile(str(scene_file.resolve()), doraise=True)
    except py_compile.PyCompileError as exc:
        return StaticCheckResult(False, str(exc), str(scene_file.resolve()))
    mypy_result = _run_optional_mypy(scene_file)
    if mypy_result:
        return StaticCheckResult(False, mypy_result, str(scene_file.resolve()))
    return StaticCheckResult(True, "", str(scene_file.resolve()))


def _run_optional_mypy(scene_file: Path) -> str:
    command = [
        sys.executable,
        "-m",
        "mypy",
        "--show-column-numbers",
        "--hide-error-context",
        "--no-color-output",
        "--no-error-summary",
        "--follow-imports",
        "skip",
        "--ignore-missing-imports",
        "--allow-untyped-globals",
        "--allow-redefinition",
        str(scene_file.resolve()),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    output = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode == 0:
        return ""
    if "No module named mypy" in output or "No module named 'mypy'" in output:
        return ""
    return output[-4000:]
