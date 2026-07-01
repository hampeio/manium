import re


def sanitize_manim_code(code: str) -> str:
    """Remove Manim patterns that commonly require LaTeX on bare Windows installs."""

    sanitized = code
    sanitized = re.sub(
        r"\n\s*summary\s*=\s*VGroup\(cn\(\"\\u5206\\u955c\\u6f14\\u793a\\u5b8c\\u6210\".*?"
        r"\n\s*self\.wait\(3\)",
        "\n        clear_active()\n        self.play(FadeOut(timeline_group), FadeOut(title), run_time=0.6)\n        self.wait(0.5)",
        sanitized,
        flags=re.DOTALL,
    )
    sanitized = re.sub(
        r"\n\s*summary\s*=\s*VGroup\(cn\(\"分镜演示完成\".*?"
        r"\n\s*self\.wait\(3\)",
        "\n        clear_active()\n        self.play(FadeOut(timeline_group), FadeOut(title), run_time=0.6)\n        self.wait(0.5)",
        sanitized,
        flags=re.DOTALL,
    )
    sanitized = re.sub(r"^\s*\w+\.add_coordinates\(\)\s*\n", "", sanitized, flags=re.MULTILINE)
    sanitized = re.sub(
        r"(\w+)\s*=\s*(\w+)\.get_x_axis_label\([\"']([^\"']+)[\"']\)",
        r'\1 = Text("\3", font="Microsoft YaHei", font_size=24, color=WHITE).next_to(\2.x_axis.get_end(), DOWN)',
        sanitized,
    )
    sanitized = re.sub(
        r"(\w+)\s*=\s*(\w+)\.get_y_axis_label\([\"']([^\"']+)[\"']\)",
        r'\1 = Text("\3", font="Microsoft YaHei", font_size=24, color=WHITE).next_to(\2.y_axis.get_end(), LEFT)',
        sanitized,
    )
    sanitized = sanitized.replace("MathTex(", "Text(")
    return sanitized
