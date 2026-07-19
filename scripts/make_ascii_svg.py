from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SOURCE_PATH: Final[Path] = ROOT / "source-prepped.png"
OUTPUT_PATH: Final[Path] = ROOT / "ascii-portrait.svg"
RAMP: Final[str] = " .`:-=+*cs#%@"
GRID_WIDTH: Final[int] = 96
CHAR_ASPECT: Final[float] = 0.54
FONT_SIZE: Final[float] = 6.2
LINE_HEIGHT: Final[float] = 7.2
CHAR_ADVANCE: Final[float] = 3.72
PANEL_WIDTH: Final[int] = 370
PANEL_PADDING_X: Final[int] = 18
PANEL_PADDING_TOP: Final[int] = 18
HEADER_HEIGHT: Final[int] = 44
BACKGROUND: Final[str] = "#0d1117"
PANEL_BG: Final[str] = "#161b22"
BORDER: Final[str] = "#30363d"
TEXT_COLOR: Final[str] = "#d0d7de"
ACCENT: Final[str] = "#58a6ff"
CURSOR_COLOR: Final[str] = "#39d353"


@dataclass(frozen=True)
class SvgConfig:
    static: bool
    width: int
    height: int


def parse_static_mode() -> bool:
    return os.environ.get("STATIC", "").strip() == "1"


def load_grayscale_image(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing preprocessed portrait: {path}. Run scripts/prep_photo.py first."
        )
    with Image.open(path) as image:
        return image.convert("L")


def resize_for_ascii(image: Image.Image) -> Image.Image:
    width, height = image.size
    rows = max(1, round((height / width) * GRID_WIDTH * CHAR_ASPECT))
    return image.resize((GRID_WIDTH, rows), Image.Resampling.LANCZOS)


def pixels_to_ascii(image: Image.Image) -> list[str]:
    ramp = np.array(list(RAMP))
    pixels = np.asarray(image, dtype=np.float32)
    normalized = 1.0 - (pixels / 255.0)
    indices = np.clip(
        np.rint(normalized * (len(RAMP) - 1)).astype(np.int32), 0, len(RAMP) - 1
    )
    indices = np.where(pixels > 247, 0, indices)
    return ["".join(ramp[row]) for row in indices]


def estimate_geometry(line_count: int) -> SvgConfig:
    content_height = max(1, round(line_count * LINE_HEIGHT))
    height = HEADER_HEIGHT + PANEL_PADDING_TOP + content_height + 28
    return SvgConfig(static=parse_static_mode(), width=PANEL_WIDTH, height=height)


def build_rows(lines: list[str], static: bool) -> str:
    rows: list[str] = []
    start_y = HEADER_HEIGHT + PANEL_PADDING_TOP + 12
    max_line_length = max((len(line) for line in lines), default=1)
    clip_width = max_line_length * CHAR_ADVANCE + 8
    row_delay = 0.04

    for index, line in enumerate(lines):
        y = start_y + index * LINE_HEIGHT
        row_id = f"row-{index}"
        clip_id = f"clip-{index}"
        line_text = escape(line).replace(" ", "&#160;")
        line_group = [
            f'<g id="{row_id}" transform="translate(0, {4 if not static else 0})" opacity="{1 if static else 0}">'
        ]

        if not static:
            line_group.append(
                f'<animateTransform attributeName="transform" type="translate" from="0,4" to="0,0" dur="0.28s" begin="{index * row_delay:.2f}s" fill="freeze" />'
            )
            line_group.append(
                f'<animate attributeName="opacity" from="0" to="1" dur="0.22s" begin="{index * row_delay:.2f}s" fill="freeze" />'
            )

        if static:
            line_group.append(
                f'<text x="{PANEL_PADDING_X}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="{FONT_SIZE}" fill="{TEXT_COLOR}" xml:space="preserve">{line_text}</text>'
            )
        else:
            line_group.append(
                f"<clipPath id=\"{clip_id}\"><rect x=\"0\" y=\"0\" width=\"0\" height=\"{LINE_HEIGHT + 2}\" rx=\"0.5\">"
                f'<animate attributeName="width" from="0" to="{clip_width:.1f}" dur="0.26s" begin="{index * row_delay:.2f}s" fill="freeze" />'
                "</rect></clipPath>"
            )
            line_group.append(
                f'<g clip-path="url(#{clip_id})">'
                f'<text x="{PANEL_PADDING_X}" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="{FONT_SIZE}" fill="{TEXT_COLOR}" xml:space="preserve">{line_text}</text>'
                "</g>"
            )
            line_group.append(
                f'<rect x="{PANEL_PADDING_X}" y="{y - FONT_SIZE + 1.4}" width="5" height="{FONT_SIZE + 1.8}" rx="0.8" fill="{CURSOR_COLOR}" opacity="0">'
                f'<animate attributeName="x" from="{PANEL_PADDING_X}" to="{PANEL_PADDING_X + clip_width:.1f}" dur="0.26s" begin="{index * row_delay:.2f}s" fill="freeze" />'
                f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;0.4;1" dur="0.28s" begin="{index * row_delay:.2f}s" fill="freeze" />'
                "</rect>"
            )

        line_group.append("</g>")
        rows.append("".join(line_group))

    return "\n".join(rows)


def build_svg(lines: list[str], static: bool) -> str:
    geometry = estimate_geometry(len(lines))
    rows_svg = build_rows(lines, static)
    title = "Abhishek ASCII portrait"
    desc = "Animated monochrome ASCII portrait generated from the uploaded head-and-shoulders photo."
    height = geometry.height

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" role="img" aria-labelledby="title desc" viewBox="0 0 {geometry.width} {height}" width="{geometry.width}" height="{height}">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(desc)}</desc>
  <rect x="0" y="0" width="{geometry.width}" height="{height}" rx="18" fill="{BACKGROUND}" />
  <rect x="10" y="10" width="{geometry.width - 20}" height="{height - 20}" rx="16" fill="{PANEL_BG}" stroke="{BORDER}" stroke-width="1.2" />

  <g transform="translate(18 22)">
    <circle cx="0" cy="0" r="4.2" fill="{CURSOR_COLOR}" />
    <circle cx="14" cy="0" r="4.2" fill="{ACCENT}" />
    <circle cx="28" cy="0" r="4.2" fill="#bc8cff" />
    <text x="44" y="4.1" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" fill="{TEXT_COLOR}">abhishek@github:~$ portrait.sh</text>
  </g>

  <line x1="18" y1="{HEADER_HEIGHT - 2}" x2="{geometry.width - 18}" y2="{HEADER_HEIGHT - 2}" stroke="{BORDER}" stroke-width="1" />
  <g>
{rows_svg}
  </g>
</svg>
"""


def main() -> int:
    try:
        image = load_grayscale_image(SOURCE_PATH)
        ascii_image = resize_for_ascii(image)
        lines = pixels_to_ascii(ascii_image)
        svg = build_svg(lines, parse_static_mode())
        OUTPUT_PATH.write_text(svg, encoding="utf-8")
        mode = "static" if parse_static_mode() else "animated"
        print(f"Saved {mode} ASCII portrait to {OUTPUT_PATH}")
        return 0
    except Exception as exc:
        print(f"make_ascii_svg.py failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

