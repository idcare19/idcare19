from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Final

import requests
from bs4 import BeautifulSoup

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
OUTPUT_PATH: Final[Path] = ROOT / "data" / "contributions.json"
USERNAME: Final[str] = "idcare19"
CONTRIBUTIONS_URL: Final[str] = f"https://github.com/users/{USERNAME}/contributions"
TIMEOUT: Final[tuple[float, float]] = (10.0, 20.0)
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Day:
    date: date
    count: int
    level: int

    @property
    def weekday(self) -> int:
        return self.date.weekday()


COUNT_RE = re.compile(r"(\d[\d,]*)\s+contributions?", re.IGNORECASE)
LEVEL_RE = re.compile(r"\b([0-4])\b")


def parse_count(text: str | None, fallback: int | None) -> int:
    if fallback is not None:
        return fallback
    if not text:
        return 0
    match = COUNT_RE.search(text)
    if match:
        return int(match.group(1).replace(",", ""))
    if "No contributions" in text:
        return 0
    if "1 contribution" in text:
        return 1
    return 0


def parse_level(element) -> int:
    for key in ("data-level", "aria-label", "title"):
        value = element.get(key)
        if value:
            match = LEVEL_RE.search(str(value))
            if match:
                return int(match.group(1))
    return 0


def parse_day(element) -> Day | None:
    raw_date = element.get("data-date")
    if not raw_date:
        return None
    try:
        parsed_date = date.fromisoformat(raw_date)
    except ValueError:
        return None

    count_attr = element.get("data-count")
    count = parse_count(element.get("aria-label") or element.get("title") or element.text, int(count_attr) if count_attr and count_attr.isdigit() else None)
    level_attr = element.get("data-level")
    level = int(level_attr) if isinstance(level_attr, str) and level_attr.isdigit() else parse_level(element)
    return Day(date=parsed_date, count=count, level=level)


def fetch_html(url: str) -> str:
    print(f"Fetching contributions HTML from {url}")
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    if not response.text.strip():
        raise RuntimeError("GitHub returned an empty contributions page.")
    return response.text


def extract_days(html: str) -> list[Day]:
    soup = BeautifulSoup(html, "html.parser")
    candidates = soup.select("[data-date]")
    days = [day for day in (parse_day(node) for node in candidates) if day is not None]

    if days:
        return sorted({day.date: day for day in days}.values(), key=lambda item: item.date)

    tooltip_candidates = soup.find_all(attrs={"aria-label": True})
    days = [day for day in (parse_day(node) for node in tooltip_candidates) if day is not None]
    if days:
        return sorted({day.date: day for day in days}.values(), key=lambda item: item.date)

    raise RuntimeError(
        "No contribution cells were found in GitHub's HTML. The page structure may have changed."
    )


def fill_missing_days(days: list[Day]) -> list[Day]:
    if not days:
        raise RuntimeError("No days to fill.")
    by_date = {day.date: day for day in days}
    start = min(by_date)
    end = max(by_date)
    filled: list[Day] = []
    current = start
    while current <= end:
        existing = by_date.get(current)
        if existing is None:
            filled.append(Day(date=current, count=0, level=0))
        else:
            filled.append(existing)
        current += timedelta(days=1)
    return filled


def current_streak(days: list[Day]) -> int:
    streak = 0
    for day in reversed(days):
        if day.count > 0:
            streak += 1
        elif streak:
            break
    return streak


def longest_streak(days: list[Day]) -> int:
    best = 0
    current = 0
    for day in days:
        if day.count > 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def best_day(days: list[Day]) -> Day:
    return max(days, key=lambda day: (day.count, -day.date.toordinal()))


def monthly_totals(days: list[Day]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for day in days:
        totals[day.date.strftime("%Y-%m")] += day.count
    return dict(sorted(totals.items()))


def build_payload(days: list[Day]) -> dict[str, object]:
    start = days[0].date.isoformat()
    end = days[-1].date.isoformat()
    best = best_day(days)
    return {
        "username": USERNAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range_start": start,
        "range_end": end,
        "total_contributions": sum(day.count for day in days),
        "current_streak": current_streak(days),
        "longest_streak": longest_streak(days),
        "best_day": {"date": best.date.isoformat(), "count": best.count},
        "monthly_totals": monthly_totals(days),
        "days": [
            {
                "date": day.date.isoformat(),
                "count": day.count,
                "level": day.level,
                "weekday": day.weekday,
            }
            for day in days
        ],
    }


def main() -> int:
    try:
        html = fetch_html(CONTRIBUTIONS_URL)
        parsed_days = extract_days(html)
        days = fill_missing_days(parsed_days)
        payload = build_payload(days)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"Saved {len(days)} contribution days to {OUTPUT_PATH} "
            f"({payload['total_contributions']} total contributions)."
        )
        return 0
    except Exception as exc:
        print(f"fetch_contributions.py failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

