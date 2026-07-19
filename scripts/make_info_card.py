from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from xml.sax.saxutils import escape

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
OUTPUT_PATH: Final[Path] = ROOT / "info-card.svg"
WIDTH: Final[int] = 490
HEIGHT: Final[int] = 560
BACKGROUND: Final[str] = "#0d1117"
PANEL_BG: Final[str] = "#161b22"
BORDER: Final[str] = "#30363d"
TEXT: Final[str] = "#f0f6fc"
SECONDARY: Final[str] = "#8b949e"
ACCENTS: Final[tuple[str, ...]] = ("#58a6ff", "#39d353", "#bc8cff", "#f0883e", "#ff7b72")


@dataclass(frozen=True)
class Row:
    label: str
    value: str


ROWS: Final[list[Row]] = [
    Row("User", "Abhishek"),
    Row("Handle", "idcare19"),
    Row("Role", "Full-Stack Developer"),
    Row("Focus", "Backend Systems & SaaS"),
    Row("Now", "Project Manager & Developer"),
    Row("Company", "Parvati and Sons"),
    Row("Frontend", "Next.js, React, Tailwind CSS"),
    Row("Backend", "Django, DRF, FastAPI"),
    Row("Database", "PostgreSQL, MongoDB"),
    Row("Tools", "Git, GitHub, Docker, Vercel, Render"),
    Row("Learning", "DSA, AI/ML, German"),
    Row("Portfolio", "idcare19.me"),
    Row("Status", "Open to opportunities"),
]

PROJECTS: Final[list[str]] = [
    "SmartQueue AI",
    "VisionSuite MVP",
    "DevVault",
    "ReqFlow AI",
    "ClientScout AI",
    "LinkPilot",
]

LEFT_ROWS: Final[list[Row]] = ROWS[:7]
RIGHT_ROWS: Final[list[Row]] = ROWS[7:]


def is_static() -> bool:
    return os.environ.get("STATIC", "").strip() == "1"


def wrap_value(value: str, max_chars: int = 34) -> list[str]:
    words = value.split()
    if not words:
        return [""]

    lines: list[str] = []
    current: list[str] = []
    for word in words:
        proposed = " ".join(current + [word])
        if current and len(proposed) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def build_column(rows: list[Row], label_x: int, value_x: int, start_y: int, static: bool, begin_offset: float) -> str:
    row_gap = 28
    lines: list[str] = []

    for index, row in enumerate(rows):
        accent = ACCENTS[(index + label_x) % len(ACCENTS)]
        y = start_y + index * row_gap
        value_lines = wrap_value(row.value, max_chars=22)
        group = [
            f'<g transform="translate(0, {4 if not static else 0})" opacity="{1 if static else 0}">'
        ]
        if not static:
            begin = begin_offset + index * 0.045
            group.append(
                f'<animateTransform attributeName="transform" type="translate" from="0,4" to="0,0" dur="0.3s" begin="{begin:.2f}s" fill="freeze" />'
            )
            group.append(
                f'<animate attributeName="opacity" from="0" to="1" dur="0.22s" begin="{begin:.2f}s" fill="freeze" />'
            )

        group.append(
            f'<text x="{label_x}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12.7" fill="{accent}">{escape(row.label)}:</text>'
        )
        for line_index, value_line in enumerate(value_lines):
            line_y = y + line_index * 15
            group.append(
                f'<text x="{value_x}" y="{line_y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12.7" fill="{TEXT}">{escape(value_line)}</text>'
            )
        group.append("</g>")
        lines.append("".join(group))

    return "\n".join(lines)


def build_rows(static: bool) -> str:
    left = build_column(LEFT_ROWS, 26, 146, 114, static, 0.00)
    right = build_column(RIGHT_ROWS, 258, 362, 114, static, 0.14)
    return "\n".join([left, right])


def build_projects(static: bool) -> str:
    delay_offset = len(ROWS) * 0.045 + 0.12
    lines: list[str] = [
        '<g transform="translate(0 0)">',
        '<text x="26" y="338" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12.8" fill="#58a6ff">Selected projects</text>',
        '<rect x="24" y="350" width="442" height="136" rx="12" fill="#0d1117" stroke="#30363d" stroke-width="1" />',
    ]

    columns = [
        (38, 58, PROJECTS[:3], 374, 0.00),
        (252, 272, PROJECTS[3:], 374, 0.08),
    ]

    for label_x, text_x, projects, base_y, column_offset in columns:
        for index, project in enumerate(projects):
            y = base_y + index * 24
            accent = ACCENTS[(index + label_x) % len(ACCENTS)]
            line = [
                f'<g transform="translate(0, {4 if not static else 0})" opacity="{1 if static else 0}">'
            ]
            if not static:
                begin = delay_offset + column_offset + index * 0.03
                line.append(
                    f'<animateTransform attributeName="transform" type="translate" from="0,4" to="0,0" dur="0.22s" begin="{begin:.2f}s" fill="freeze" />'
                )
                line.append(
                    f'<animate attributeName="opacity" from="0" to="1" dur="0.18s" begin="{begin:.2f}s" fill="freeze" />'
                )
            line.append(
                f'<text x="{label_x}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12.3" fill="{accent}">▸</text>'
            )
            line.append(
                f'<text x="{text_x}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12.3" fill="{TEXT}">{escape(project)}</text>'
            )
            line.append("</g>")
            lines.append("".join(line))

    lines.append("</g>")
    return "\n".join(lines)


def build_svg(static: bool) -> str:
    row_block = build_rows(static)
    project_block = build_projects(static)
    animation_note = "static" if static else "animated"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">
  <title id="title">Abhishek developer information card</title>
  <desc id="desc">Terminal-style neofetch card showing profile details, technology stack, and selected projects.</desc>
  <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="18" fill="{BACKGROUND}" />
  <rect x="10" y="10" width="{WIDTH - 20}" height="{HEIGHT - 20}" rx="16" fill="{PANEL_BG}" stroke="{BORDER}" stroke-width="1.2" />

  <g transform="translate(24 24)">
    <circle cx="0" cy="0" r="4.2" fill="#ff7b72" />
    <circle cx="14" cy="0" r="4.2" fill="#f0883e" />
    <circle cx="28" cy="0" r="4.2" fill="#39d353" />
    <text x="44" y="4" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" fill="{TEXT}">abhishek@github:~$ neofetch</text>
  </g>

  <text x="26" y="74" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12" fill="{SECONDARY}">Profile snapshot</text>
  <line x1="24" y1="88" x2="{WIDTH - 24}" y2="88" stroke="{BORDER}" stroke-width="1" />

  {row_block}
  {project_block}

  <text x="26" y="550" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" fill="{SECONDARY}">Rendered as {escape(animation_note)} SVG with freeze-once terminal animation.</text>
</svg>
"""


def main() -> int:
    try:
        OUTPUT_PATH.write_text(build_svg(is_static()), encoding="utf-8")
        print(f"Saved info card to {OUTPUT_PATH}")
        return 0
    except Exception as exc:
        print(f"make_info_card.py failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
