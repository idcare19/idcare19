from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Final
from xml.sax.saxutils import escape

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
INPUT_PATH: Final[Path] = ROOT / "data" / "contributions.json"
OUTPUT_PATH: Final[Path] = ROOT / "contrib-heatmap.svg"
WIDTH: Final[int] = 860
HEIGHT: Final[int] = 260
BACKGROUND: Final[str] = "#0d1117"
PANEL_BG: Final[str] = "#161b22"
BORDER: Final[str] = "#30363d"
TEXT: Final[str] = "#f0f6fc"
SECONDARY: Final[str] = "#8b949e"
PALETTE: Final[list[str]] = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",
]
CELL_SIZE: Final[int] = 12
CELL_GAP: Final[int] = 4
LEFT_MARGIN: Final[int] = 82
TOP_MARGIN: Final[int] = 56
RIGHT_PADDING: Final[int] = 26
BOTTOM_PADDING: Final[int] = 24


@dataclass(frozen=True)
class Day:
    date: date
    count: int
    level: int
    weekday: int


def is_static() -> bool:
    return os.environ.get("STATIC", "").strip() == "1"


def load_data(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing contribution data: {path}. Run scripts/fetch_contributions.py first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def to_day(item: dict[str, object]) -> Day:
    return Day(
        date=date.fromisoformat(str(item["date"])),
        count=int(item["count"]),
        level=int(item.get("level", 0)),
        weekday=int(item.get("weekday", date.fromisoformat(str(item["date"])).weekday())),
    )


def load_days(payload: dict[str, object]) -> list[Day]:
    days = [to_day(item) for item in payload.get("days", [])]
    if not days:
        raise RuntimeError("Contribution dataset is empty.")
    return sorted(days, key=lambda item: item.date)


def fill_grid(days: list[Day], range_end: date | None = None) -> dict[date, Day]:
    by_date = {day.date: day for day in days}
    if range_end is None:
        range_end = max(by_date)
    saturday_offset = (5 - range_end.weekday()) % 7
    grid_end = range_end + timedelta(days=saturday_offset)
    grid_start = grid_end - timedelta(days=370)
    filled: dict[date, Day] = {}

    current = grid_start
    while current <= grid_end:
        existing = by_date.get(current)
        if existing is None:
            filled[current] = Day(date=current, count=0, level=0, weekday=current.weekday())
        else:
            filled[current] = existing
        current += timedelta(days=1)
    return filled


def month_labels(grid_days: dict[date, Day]) -> list[tuple[str, int]]:
    labels: list[tuple[str, int]] = []
    seen: set[tuple[int, int]] = set()
    for current in sorted(grid_days):
        if current.day != 1:
            continue
        marker = (current.year, current.month)
        if marker in seen:
            continue
        seen.add(marker)
        week_index = ((current - min(grid_days)).days) // 7
        labels.append((current.strftime("%b"), week_index))
    return labels


def clamp_level(level: int) -> int:
    return max(0, min(level, len(PALETTE) - 1))


def cell_color(day: Day) -> str:
    if day.count <= 0:
        return PALETTE[0]
    if day.level:
        return PALETTE[clamp_level(day.level)]
    if day.count <= 1:
        return PALETTE[1]
    if day.count <= 3:
        return PALETTE[2]
    if day.count <= 6:
        return PALETTE[3]
    if day.count <= 10:
        return PALETTE[4]
    return PALETTE[5]


def square_animation(index: int, static: bool) -> str:
    if static:
        return ""
    delay = index * 0.008
    return (
        f'<animateTransform attributeName="transform" type="translate" from="0,-5" to="0,0" dur="0.32s" begin="{delay:.3f}s" fill="freeze" />'
        f'<animate attributeName="opacity" from="0" to="1" dur="0.18s" begin="{delay:.3f}s" fill="freeze" />'
    )


def build_grid(days: dict[date, Day], static: bool, grid_start: date) -> str:
    output: list[str] = []
    sorted_days = [days[grid_start + timedelta(days=i)] for i in range(53 * 7)]

    for index, day in enumerate(sorted_days):
        week = index // 7
        weekday = index % 7
        x = LEFT_MARGIN + week * (CELL_SIZE + CELL_GAP)
        y = TOP_MARGIN + weekday * (CELL_SIZE + CELL_GAP)
        color = cell_color(day)
        output.append(
            f'<g transform="translate(0, 0)" opacity="{1 if static else 0}">'
            f'<rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="3" ry="3" fill="{color}" stroke="#1f2937" stroke-width="0.4">'
            f"{square_animation(index, static)}"
            "</rect>"
            "</g>"
        )
    return "\n".join(output)


def build_month_labels_block(labels: list[tuple[str, int]]) -> str:
    parts = [
        f'<text x="{LEFT_MARGIN}" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12" fill="{SECONDARY}">Months</text>'
    ]
    for month, week_index in labels:
        x = LEFT_MARGIN + week_index * (CELL_SIZE + CELL_GAP)
        parts.append(
            f'<text x="{x}" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11.5" fill="{SECONDARY}">{escape(month)}</text>'
        )
    return "\n".join(parts)


def build_weekday_labels() -> str:
    labels = [("Mon", 1), ("Wed", 3), ("Fri", 5)]
    parts: list[str] = []
    for label, weekday in labels:
        y = TOP_MARGIN + weekday * (CELL_SIZE + CELL_GAP) + 10
        parts.append(
            f'<text x="24" y="{y}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11.5" fill="{SECONDARY}">{label}</text>'
        )
    return "\n".join(parts)


def format_best_day(payload: dict[str, object]) -> str:
    best = payload.get("best_day", {})
    if not isinstance(best, dict):
        return "n/a"
    return f"{best.get('date', 'n/a')} ({best.get('count', 0)})"


def stats_text(payload: dict[str, object]) -> str:
    total = int(payload.get("total_contributions", 0))
    current = int(payload.get("current_streak", 0))
    longest = int(payload.get("longest_streak", 0))
    return (
        f"Total contributions: {total}   "
        f"Current streak: {current}   "
        f"Longest streak: {longest}   "
        f"Best day: {format_best_day(payload)}"
    )


def legend() -> str:
    x = WIDTH - RIGHT_PADDING - 160
    y = 42
    parts = [
        f'<text x="{x - 42}" y="{y + 9}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" fill="{SECONDARY}">Less</text>'
    ]
    for index, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="{x + index * 18}" y="{y}" width="12" height="12" rx="3" fill="{color}" stroke="#1f2937" stroke-width="0.4" />'
        )
    parts.append(
        f'<text x="{x + len(PALETTE) * 18 + 6}" y="{y + 9}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" fill="{SECONDARY}">More</text>'
    )
    return "\n".join(parts)


def build_svg(payload: dict[str, object], days: list[Day], static: bool) -> str:
    range_end = date.fromisoformat(str(payload["range_end"]))
    grid = fill_grid(days, range_end)
    grid_start = min(grid)
    month_block = build_month_labels_block(month_labels(grid))
    weekday_block = build_weekday_labels()
    legend_block = legend()
    grid_block = build_grid(grid, static, grid_start)
    generated = payload.get("generated_at", "")
    if isinstance(generated, str):
        timestamp = generated.replace("T", " ", 1).replace("+00:00", " UTC")
    else:
        timestamp = "unknown"
    title = f"{payload.get('username', 'idcare19')} contributions"
    desc = "GitHub-style animated contribution calendar rendered directly in SVG."

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(desc)}</desc>
  <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="18" fill="{BACKGROUND}" />
  <rect x="10" y="10" width="{WIDTH - 20}" height="{HEIGHT - 20}" rx="16" fill="{PANEL_BG}" stroke="{BORDER}" stroke-width="1.2" />

  <g transform="translate(24 24)">
    <circle cx="0" cy="0" r="4.2" fill="#39d353" />
    <circle cx="14" cy="0" r="4.2" fill="#58a6ff" />
    <circle cx="28" cy="0" r="4.2" fill="#bc8cff" />
    <text x="44" y="4" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11" fill="{TEXT}">abhishek@github:~$ contributions.sh</text>
  </g>

  <text x="24" y="74" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12.2" fill="{TEXT}">{escape(str(payload.get("username", "idcare19")))} / contribution heatmap</text>
  <text x="24" y="92" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10.8" fill="{SECONDARY}">Last updated: {escape(timestamp)}</text>
  <line x1="24" y1="104" x2="{WIDTH - 24}" y2="104" stroke="{BORDER}" stroke-width="1" />

  {month_block}
  {weekday_block}
  {grid_block}

  <g transform="translate(24 210)">
    <text x="0" y="0" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="11.3" fill="{TEXT}">{escape(stats_text(payload))}</text>
  </g>
  <g>
  <text x="24" y="232" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="10.8" fill="{SECONDARY}">Profile activity rendered from public GitHub HTML.</text>
    {legend_block}
  </g>
</svg>
"""


def main() -> int:
    try:
        payload = load_data(INPUT_PATH)
        days = load_days(payload)
        svg = build_svg(payload, days, is_static())
        OUTPUT_PATH.write_text(svg, encoding="utf-8")
        print(f"Saved heatmap SVG to {OUTPUT_PATH}")
        return 0
    except Exception as exc:
        print(f"render_heatmap_svg.py failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
