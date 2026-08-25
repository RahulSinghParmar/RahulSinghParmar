"""Generate a GitHub-canvas-matched 3D contribution calendar.

Usage:
    python scripts/generate_isocalendar.py assets/profile-data.json assets/metrics.isocalendar-dark.svg --theme dark
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def polygon(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def cube(x: float, y: float, height: float, level: int) -> str:
    half_width, half_depth = 9.5, 4.8
    top_y = y - height
    top = [(x, top_y - half_depth), (x + half_width, top_y), (x, top_y + half_depth), (x - half_width, top_y)]
    left = [(x - half_width, top_y), (x, top_y + half_depth), (x, y + half_depth), (x - half_width, y)]
    right = [(x + half_width, top_y), (x, top_y + half_depth), (x, y + half_depth), (x + half_width, y)]
    return (
        f'<g class="cube l{level}">'
        f'<polygon class="left" points="{polygon(left)}"/>'
        f'<polygon class="right" points="{polygon(right)}"/>'
        f'<polygon class="top" points="{polygon(top)}"/>'
        f'</g>'
    )


def longest_streak(contributions: list[dict[str, object]]) -> int:
    best = current = 0
    for item in contributions:
        if int(item["count"]) > 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


PALETTES = {
    "dark": {
        "background": "#0d1117", "title": "#e6edf3", "muted": "#8b949e", "stroke": "#0d1117",
        "levels": [
            ("#21262d", "#161b22", "#1f242b"),
            ("#0e4429", "#0b3a22", "#0d4127"),
            ("#006d32", "#005d2b", "#00662f"),
            ("#26a641", "#1f883d", "#239b3f"),
            ("#39d353", "#2ea043", "#34b748"),
        ],
    },
    "light": {
        "background": "#ffffff", "title": "#24292f", "muted": "#57606a", "stroke": "#ffffff",
        "levels": [
            ("#ebedf0", "#d0d7de", "#e1e5e9"),
            ("#9be9a8", "#7fd88f", "#8ce39b"),
            ("#40c463", "#2da44e", "#36b75a"),
            ("#30a14e", "#1f883d", "#269544"),
            ("#216e39", "#175c2f", "#1c6634"),
        ],
    },
}


def render(source: Path, destination: Path, theme: str = "dark") -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    contributions = payload["contributions"]
    if not contributions:
        raise ValueError("Contribution data is empty")

    first_day = date.fromisoformat(contributions[0]["date"])
    total = sum(int(item["count"]) for item in contributions)
    active_days = sum(int(item["count"]) > 0 for item in contributions)
    streak = longest_streak(contributions)
    year_label = f'{first_day.strftime("%b %Y")}—{date.fromisoformat(contributions[-1]["date"]).strftime("%b %Y")}'

    cubes: list[tuple[int, str]] = []
    step_x, step_y = 13.4, 5.8
    origin_x, origin_y = 176.0, 112.0
    for index, item in enumerate(contributions):
        current = date.fromisoformat(item["date"])
        week = (current - first_day).days // 7
        day = (current.weekday() + 1) % 7
        level = max(0, min(int(item["level"]), 4))
        count = int(item["count"])
        height = 2.0 if level == 0 else 5.0 + level * 5.4 + min(count, 8) * 0.7
        x = origin_x + (week - day) * step_x
        y = origin_y + (week + day) * step_y
        cubes.append((week + day, cube(x, y, height, level)))

    cubes.sort(key=lambda item: item[0])
    cube_markup = "".join(markup for _, markup in cubes)
    legend = "".join(
        cube(830 + level * 27, 446, 2 if level == 0 else 5 + level * 4, level)
        for level in range(5)
    )

    palette = PALETTES[theme]
    level_styles = "\n    ".join(
        f'.l{index} .top {{ fill:{top} }} .l{index} .left {{ fill:{left} }} .l{index} .right {{ fill:{right} }}'
        for index, (top, left, right) in enumerate(palette["levels"])
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="480" viewBox="0 0 1000 480" role="img" aria-labelledby="calendar-title calendar-desc">
  <title id="calendar-title">Rahul Singh Parmar's isometric GitHub contribution calendar</title>
  <desc id="calendar-desc">{total} public contributions across {active_days} active days from {year_label}, shown as three-dimensional cubes.</desc>
  <style>
    .title {{ fill:{palette["title"]} }} .meta,.legend-label {{ fill:{palette["muted"]} }}
    {level_styles}
    .cube polygon {{ stroke:{palette["stroke"]}; stroke-opacity:.58; stroke-width:.45 }}
  </style>
  <rect width="100%" height="100%" fill="{palette["background"]}"/>
  <text class="title" x="38" y="38" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700">A year in commits</text>
  <text class="meta" x="38" y="62" font-family="Segoe UI, Arial, sans-serif" font-size="12">{total} contributions · {active_days} active days · {streak}-day longest streak</text>
  <g>{cube_markup}</g>
  <text class="meta" x="38" y="451" font-family="Segoe UI, Arial, sans-serif" font-size="11">{year_label} · public activity</text>
  <text class="legend-label" x="778" y="62" font-family="Segoe UI, Arial, sans-serif" font-size="11">less</text>
  <g transform="translate(0 -389)">{legend}</g>
  <text class="legend-label" x="968" y="62" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="11">more</text>
</svg>
'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(svg, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--theme", choices=("light", "dark"), default="dark")
    arguments = parser.parse_args()
    render(arguments.source, arguments.destination, arguments.theme)


if __name__ == "__main__":
    main()
