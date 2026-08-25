"""Fetch public GitHub data and render reliable, repository-hosted profile SVGs.

The renderer uses only the Python standard library. Network access is optional:

    python scripts/build_profile_assets.py --fetch
    python scripts/build_profile_assets.py

Set GITHUB_TOKEN in CI to raise GitHub API rate limits. The token is never stored.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


USERNAME = "RahulSinghParmar"
ACCENT = "#39d353"


@dataclass(frozen=True)
class Theme:
    name: str
    background: str
    surface: str
    text: str
    muted: str
    grid: str
    border: str
    accent: str
    accent_fill: str


THEMES = {
    "dark": Theme("dark", "#0d1117", "#0d1117", "#e6edf3", "#8b949e", "#30363d", "#30363d", ACCENT, "#123d24"),
    "light": Theme("light", "#ffffff", "#ffffff", "#24292f", "#57606a", "#d0d7de", "#d0d7de", "#1a7f37", "#dafbe1"),
}

LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Python": "#3572A5",
    "Java": "#b07219",
    "TeX": "#3D6117",
    "Shell": "#89e051",
    "Lua": "#000080",
    "TypeScript": "#3178c6",
}


def request_json(url: str, token: str | None = None, attempts: int = 3) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RahulSinghParmar-profile-assets",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to fetch {url} after {attempts} attempts") from last_error


def collect_public_data(username: str) -> dict[str, Any]:
    token = os.getenv("GITHUB_TOKEN")
    user = request_json(f"https://api.github.com/users/{username}", token)
    repos = request_json(
        f"https://api.github.com/users/{username}/repos?per_page=100&type=owner&sort=updated",
        token,
    )
    originals = [repo for repo in repos if not repo["fork"] and not repo["archived"]]

    language_totals: dict[str, int] = {}
    for repo in originals:
        if repo["name"].casefold() == username.casefold():
            continue
        for language, byte_count in request_json(repo["languages_url"], token).items():
            language_totals[language] = language_totals.get(language, 0) + int(byte_count)

    contribution_data = request_json(
        f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
    )
    compact_repos = [
        {
            "name": repo["name"],
            "html_url": repo["html_url"],
            "description": repo["description"] or "",
            "language": repo["language"] or "",
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "updated_at": repo["updated_at"],
        }
        for repo in originals
    ]
    return {
        "user": {
            "login": user["login"],
            "name": user.get("name") or username,
            "public_repos": user["public_repos"],
            "followers": user["followers"],
            "following": user["following"],
            "html_url": user["html_url"],
        },
        "repos": compact_repos,
        "languages": language_totals,
        "contributions": contribution_data["contributions"],
    }


def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def svg_open(width: int, height: int, title: str, theme: Theme) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
  <title>{html.escape(title)}</title>
  <rect width="{width}" height="{height}" fill="{theme.background}"/>
'''


def radar_points(values: list[float], cx: float, cy: float, radius: float) -> list[tuple[float, float]]:
    count = len(values)
    return [
        (
            cx + radius * value * math.cos(-math.pi / 2 + 2 * math.pi * index / count),
            cy + radius * value * math.sin(-math.pi / 2 + 2 * math.pi * index / count),
        )
        for index, value in enumerate(values)
    ]


def points_attribute(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def render_radar(labels: list[str], values: list[float], title: str, theme: Theme) -> str:
    width, height = 540, 500
    cx, cy, radius = 270, 260, 158
    angles = [-math.pi / 2 + 2 * math.pi * index / len(labels) for index in range(len(labels))]
    grid = []
    for level in (0.25, 0.5, 0.75, 1.0):
        ring = radar_points([level] * len(labels), cx, cy, radius)
        grid.append(f'<polygon points="{points_attribute(ring)}" fill="none" stroke="{theme.grid}" stroke-width="1"/>')
    axes = []
    label_markup = []
    for label, angle in zip(labels, angles):
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{theme.grid}"/>')
        lx = cx + (radius + 34) * math.cos(angle)
        ly = cy + (radius + 34) * math.sin(angle)
        if abs(lx - cx) < 20:
            anchor = "middle"
        elif lx > cx:
            anchor = "start"
            lx = min(lx, width - 102)
        else:
            anchor = "end"
            lx = max(lx, 102)
        label_markup.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" fill="{theme.text}" font-size="13">{html.escape(label)}</text>'
        )
    data = radar_points(values, cx, cy, radius)
    nodes = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{theme.accent}"/>' for x, y in data
    )
    return (
        svg_open(width, height, title, theme)
        + f'''  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="270" y="30" text-anchor="middle" fill="{theme.text}" font-size="17" font-weight="700">{html.escape(title)}</text>
    {''.join(grid)}{''.join(axes)}
    <polygon points="{points_attribute(data)}" fill="{theme.accent_fill}" fill-opacity="0.76" stroke="{theme.accent}" stroke-width="2.5"/>
    {nodes}{''.join(label_markup)}
  </g>
</svg>
'''
    )


def streaks(contributions: list[dict[str, Any]]) -> tuple[int, int, int]:
    best = current_run = active_days = 0
    for item in contributions:
        if int(item["count"]) > 0:
            current_run += 1
            active_days += 1
            best = max(best, current_run)
        else:
            current_run = 0
    trailing = 0
    for item in reversed(contributions):
        if int(item["count"]) > 0:
            trailing += 1
        elif trailing:
            break
    return trailing, best, active_days


def render_stats(data: dict[str, Any], theme: Theme) -> str:
    width, height = 720, 220
    repos = data["repos"]
    total_stars = sum(int(repo["stars"]) for repo in repos)
    contributions = data["contributions"]
    total_contributions = sum(int(item["count"]) for item in contributions)
    _, longest, active_days = streaks(contributions)
    metrics = [
        (str(total_stars), "Stars on original repos"),
        (str(data["user"]["public_repos"]), "Public repositories"),
        (str(data["user"]["followers"]), "Followers"),
        (str(total_contributions), "Contributions (1y)"),
        (str(active_days), "Active days (1y)"),
        (str(longest), "Longest streak"),
    ]
    cells = []
    for index, (value, label) in enumerate(metrics):
        column, row = index % 3, index // 3
        x, y = 28 + column * 230, 86 + row * 74
        cells.append(
            f'<text x="{x}" y="{y}" fill="{theme.text}" font-size="27" font-weight="700">{html.escape(value)}</text>'
            f'<text x="{x}" y="{y + 22}" fill="{theme.muted}" font-size="12">{html.escape(label)}</text>'
        )
    return (
        svg_open(width, height, "RahulSinghParmar GitHub statistics", theme)
        + f'''  <rect x="1" y="1" width="718" height="218" rx="14" fill="none" stroke="{theme.border}"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="28" y="38" fill="{theme.accent}" font-size="17" font-weight="700">RahulSinghParmar</text>
    <text x="692" y="38" text-anchor="end" fill="{theme.muted}" font-size="12">at a glance</text>
    <line x1="28" y1="52" x2="692" y2="52" stroke="{theme.grid}"/>
    {''.join(cells)}
  </g>
</svg>
'''
    )


def top_languages(data: dict[str, Any], limit: int = 7) -> list[tuple[str, int, float]]:
    items = sorted(data["languages"].items(), key=lambda item: item[1], reverse=True)[:limit]
    total = sum(byte_count for _, byte_count in items) or 1
    return [(name, byte_count, byte_count / total * 100) for name, byte_count in items]


def render_language_bars(data: dict[str, Any], theme: Theme) -> str:
    width, height = 720, 192
    languages = top_languages(data, 6)
    rows = []
    for index, (name, _, percentage) in enumerate(languages):
        y = 58 + index * 22
        bar_width = 460 * percentage / max(languages[0][2], 1)
        color = LANGUAGE_COLORS.get(name, theme.accent)
        rows.append(
            f'<text x="25" y="{y + 9}" fill="{theme.text}" font-size="12">{html.escape(name)}</text>'
            f'<rect x="135" y="{y}" width="{bar_width:.1f}" height="12" rx="6" fill="{color}"/>'
            f'<text x="695" y="{y + 10}" text-anchor="end" fill="{theme.muted}" font-size="11">{percentage:.1f}%</text>'
        )
    return (
        svg_open(width, height, "Language mix across original repositories", theme)
        + f'''  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="25" y="28" fill="{theme.text}" font-size="16" font-weight="700">Language mix · original repositories</text>
    {''.join(rows)}
  </g>
</svg>
'''
    )


def render_achievements(data: dict[str, Any], project_count: int, theme: Theme) -> str:
    width, height = 900, 170
    original_repos = len(data["repos"])
    items = [
        ("4+", "years in infrastructure"),
        ("LEAD", "network engineering"),
        ("B.E.", "computer engineering"),
        (str(project_count), "selected builds"),
        (str(original_repos), "original repositories"),
    ]
    gap = 180
    connectors = []
    nodes = []
    for index, (value, label) in enumerate(items):
        x = 90 + index * gap
        if index < len(items) - 1:
            connectors.append(f'<line x1="{x + 24}" y1="72" x2="{x + gap - 24}" y2="72" stroke="{theme.grid}" stroke-width="2"/>')
        nodes.append(
            f'<circle cx="{x}" cy="72" r="25" fill="{theme.background}" stroke="{theme.accent}" stroke-width="2"/>'
            f'<text x="{x}" y="77" text-anchor="middle" fill="{theme.accent}" font-size="13" font-weight="700">{html.escape(value)}</text>'
            f'<text x="{x}" y="119" text-anchor="middle" fill="{theme.text}" font-size="12">{html.escape(label)}</text>'
        )
    return (
        svg_open(width, height, "Career and project milestones", theme)
        + f'''  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="450" y="24" text-anchor="middle" fill="{theme.muted}" font-size="11" letter-spacing="1.5">SIGNAL PATH · EXPERIENCE TO SHIPPED WORK</text>
    {''.join(connectors)}{''.join(nodes)}
  </g>
</svg>
'''
    )


def render_achievements_mobile(data: dict[str, Any], project_count: int, theme: Theme) -> str:
    width, height = 420, 520
    items = [
        ("4+", "years in infrastructure"),
        ("LEAD", "network engineering"),
        ("B.E.", "computer engineering"),
        (str(project_count), "selected builds"),
        (str(len(data["repos"])), "original repositories"),
    ]
    nodes = []
    for index, (value, label) in enumerate(items):
        y = 92 + index * 88
        if index < len(items) - 1:
            nodes.append(f'<line x1="74" y1="{y + 25}" x2="74" y2="{y + 63}" stroke="{theme.grid}" stroke-width="2"/>')
        nodes.append(
            f'<circle cx="74" cy="{y}" r="25" fill="{theme.background}" stroke="{theme.accent}" stroke-width="2"/>'
            f'<text x="74" y="{y + 5}" text-anchor="middle" fill="{theme.accent}" font-size="13" font-weight="700">{html.escape(value)}</text>'
            f'<text x="118" y="{y + 5}" fill="{theme.text}" font-size="14">{html.escape(label)}</text>'
        )
    return (
        svg_open(width, height, "Career and project milestones", theme)
        + f'''  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="210" y="30" text-anchor="middle" fill="{theme.muted}" font-size="11" letter-spacing="1.3">EXPERIENCE TO SHIPPED WORK</text>
    {''.join(nodes)}
  </g>
</svg>
'''
    )


def render_project_card(config: dict[str, Any], repo: dict[str, Any], theme: Theme) -> str:
    width, height = 420, 184
    description = config["description"] or repo.get("description") or "Public GitHub project"
    lines = textwrap.wrap(description, width=58)[:2]
    impact_lines = textwrap.wrap(f'Why it matters · {config["impact"]}', width=58)[:2]
    stack = "  ·  ".join(config["stack"])
    language = repo.get("language") or config["stack"][0]
    color = LANGUAGE_COLORS.get(language, theme.accent)
    description_markup = "".join(
        f'<text x="18" y="{58 + index * 17}" fill="{theme.text}" font-size="12">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    impact_markup = "".join(
        f'<text x="18" y="{103 + index * 16}" fill="{theme.text}" font-size="11">{html.escape(line)}</text>'
        for index, line in enumerate(impact_lines)
    )
    return (
        svg_open(width, height, config["title"], theme)
        + f'''  <rect x="1" y="1" width="418" height="182" rx="13" fill="none" stroke="{theme.border}"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="18" y="31" fill="{theme.muted}" font-size="14">▣</text>
    <text x="40" y="31" fill="{theme.accent}" font-size="16" font-weight="700">{html.escape(config["title"])}</text>
    {description_markup}
    {impact_markup}
    <circle cx="22" cy="151" r="5" fill="{color}"/>
    <text x="34" y="155" fill="{theme.muted}" font-size="11">{html.escape(stack)}</text>
    <text x="18" y="175" fill="{theme.muted}" font-size="11">★ {repo.get("stars", 0)}    ⑂ {repo.get("forks", 0)}</text>
  </g>
</svg>
'''
    )


def render_infrastructure(theme: Theme) -> str:
    width, height = 1000, 220
    nodes = [
        (95, "USERS", "requests"),
        (270, "EDGE", "DNS · VPN"),
        (455, "NETWORK", "VLAN · routing"),
        (640, "SYSTEMS", "Linux · Windows"),
        (825, "CLOUD", "AWS · services"),
    ]
    boxes = []
    paths = []
    for index, (x, label, subtitle) in enumerate(nodes):
        boxes.append(
            f'<rect x="{x - 65}" y="82" width="130" height="64" rx="9" fill="{theme.surface}" stroke="{theme.border}"/>'
            f'<text x="{x}" y="107" text-anchor="middle" fill="{theme.accent}" font-size="13" font-weight="700">{label}</text>'
            f'<text x="{x}" y="127" text-anchor="middle" fill="{theme.muted}" font-size="11">{subtitle}</text>'
        )
        if index < len(nodes) - 1:
            x2 = nodes[index + 1][0]
            paths.append(f'<path id="link{index}" d="M{x + 65} 114 H{x2 - 65}" stroke="{theme.grid}" stroke-width="2"/>')
            paths.append(
                f'<circle r="4" fill="{theme.accent}" opacity="0"><animate attributeName="opacity" from="0" to="1" dur=".1s" fill="freeze"/><animateMotion dur="{1.8 + index * .25:.2f}s" repeatCount="indefinite"><mpath href="#link{index}"/></animateMotion></circle>'
            )
    return (
        svg_open(width, height, "Infrastructure delivery path", theme)
        + f'''  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="500" y="30" text-anchor="middle" fill="{theme.text}" font-size="17" font-weight="700">from packet to platform</text>
    <text x="500" y="52" text-anchor="middle" fill="{theme.muted}" font-size="12">observe · secure · automate · recover</text>
    {''.join(paths)}{''.join(boxes)}
    <path d="M455 146 V181 H825 V146" fill="none" stroke="{theme.accent}" stroke-opacity=".5" stroke-dasharray="5 6"/>
    <text x="640" y="202" text-anchor="middle" fill="{theme.muted}" font-size="11">monitoring + security feedback loop</text>
  </g>
</svg>
'''
    )


def render_infrastructure_mobile(theme: Theme) -> str:
    width, height = 420, 540
    nodes = [
        (100, "USERS", "requests"),
        (194, "EDGE", "DNS · VPN"),
        (288, "NETWORK", "VLAN · routing"),
        (382, "SYSTEMS", "Linux · Windows"),
        (476, "CLOUD", "AWS · services"),
    ]
    boxes = []
    paths = []
    for index, (y, label, subtitle) in enumerate(nodes):
        boxes.append(
            f'<rect x="90" y="{y - 30}" width="240" height="60" rx="9" fill="{theme.surface}" stroke="{theme.border}"/>'
            f'<text x="210" y="{y - 4}" text-anchor="middle" fill="{theme.accent}" font-size="14" font-weight="700">{label}</text>'
            f'<text x="210" y="{y + 16}" text-anchor="middle" fill="{theme.muted}" font-size="12">{subtitle}</text>'
        )
        if index < len(nodes) - 1:
            next_y = nodes[index + 1][0]
            paths.append(f'<path id="mobile-link{index}" d="M210 {y + 30} V{next_y - 30}" stroke="{theme.grid}" stroke-width="2"/>')
            paths.append(
                f'<circle r="4" fill="{theme.accent}"><animateMotion dur="{1.6 + index * .2:.2f}s" repeatCount="indefinite"><mpath href="#mobile-link{index}"/></animateMotion></circle>'
            )
    return (
        svg_open(width, height, "Infrastructure delivery path", theme)
        + f'''  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="210" y="27" text-anchor="middle" fill="{theme.text}" font-size="17" font-weight="700">from packet to platform</text>
    <text x="210" y="48" text-anchor="middle" fill="{theme.muted}" font-size="12">observe · secure · automate · recover</text>
    {''.join(paths)}{''.join(boxes)}
    <text x="210" y="526" text-anchor="middle" fill="{theme.muted}" font-size="11">monitoring + security feedback loop</text>
  </g>
</svg>
'''
    )


def render_automation_loop(theme: Theme) -> str:
    width, height = 1000, 190
    labels = ["OBSERVE", "DETECT", "AUTOMATE", "RECOVER", "LEARN"]
    xs = [90, 290, 500, 710, 910]
    path = "M90 84 H910"
    nodes = []
    for x, label in zip(xs, labels):
        nodes.append(
            f'<circle cx="{x}" cy="84" r="13" fill="{theme.background}" stroke="{theme.accent}" stroke-width="2"/>'
            f'<circle cx="{x}" cy="84" r="4" fill="{theme.accent}"/>'
            f'<text x="{x}" y="119" text-anchor="middle" fill="{theme.text}" font-size="12" font-weight="700">{label}</text>'
        )
    return (
        svg_open(width, height, "Automation engineering feedback loop", theme)
        + f'''  <g font-family="JetBrains Mono, Consolas, monospace">
    <text x="28" y="29" fill="{theme.muted}" font-size="12">$ ./keep-systems-reliable --continuous</text>
    <path id="automation-path" d="{path}" stroke="{theme.grid}" stroke-width="2"/>
    {''.join(nodes)}
    <circle r="7" fill="{theme.accent}" opacity="0"><animate attributeName="opacity" from="0" to="1" dur=".1s" fill="freeze"/><animateMotion dur="5s" repeatCount="indefinite"><mpath href="#automation-path"/></animateMotion></circle>
    <text x="28" y="164" fill="{theme.accent}" font-size="12">status: operational</text>
    <text x="972" y="164" text-anchor="end" fill="{theme.muted}" font-size="10">01100001 01110101 01110100 01101111 01101101 01100001 01110100 01100101</text>
  </g>
</svg>
'''
    )


def render_automation_loop_mobile(theme: Theme) -> str:
    width, height = 420, 520
    labels = ["OBSERVE", "DETECT", "AUTOMATE", "RECOVER", "LEARN"]
    ys = [94, 180, 266, 352, 438]
    path = "M84 94 V438"
    nodes = []
    for y, label in zip(ys, labels):
        nodes.append(
            f'<circle cx="84" cy="{y}" r="13" fill="{theme.background}" stroke="{theme.accent}" stroke-width="2"/>'
            f'<circle cx="84" cy="{y}" r="4" fill="{theme.accent}"/>'
            f'<text x="122" y="{y + 5}" fill="{theme.text}" font-size="14" font-weight="700">{label}</text>'
        )
    return (
        svg_open(width, height, "Automation engineering feedback loop", theme)
        + f'''  <g font-family="JetBrains Mono, Consolas, monospace">
    <text x="22" y="28" fill="{theme.muted}" font-size="11">$ ./keep-systems-reliable --continuous</text>
    <path id="automation-mobile-path" d="{path}" stroke="{theme.grid}" stroke-width="2"/>
    {''.join(nodes)}
    <circle r="7" fill="{theme.accent}"><animateMotion dur="5s" repeatCount="indefinite"><mpath href="#automation-mobile-path"/></animateMotion></circle>
    <text x="22" y="500" fill="{theme.accent}" font-size="12">status: operational · automate</text>
  </g>
</svg>
'''
    )


def render_all(data: dict[str, Any], data_path: Path, skills_path: Path, projects_path: Path, output: Path) -> None:
    from generate_isocalendar import render as render_isocalendar

    skills = json.loads(skills_path.read_text(encoding="utf-8"))["skills"]
    projects = json.loads(projects_path.read_text(encoding="utf-8"))
    repo_lookup = {repo["name"].casefold(): repo for repo in data["repos"]}
    language_items = top_languages(data, 7)
    language_labels = [name for name, _, _ in language_items]
    maximum = max((byte_count for _, byte_count, _ in language_items), default=1)
    language_values = [max(0.08, byte_count / maximum) for _, byte_count, _ in language_items]

    for theme_name, theme in THEMES.items():
        write_svg(
            output / f"radar-skills-{theme_name}.svg",
            render_radar([skill["label"] for skill in skills], [skill["value"] / 100 for skill in skills], "Skill radar", theme),
        )
        write_svg(
            output / f"radar-languages-{theme_name}.svg",
            render_radar(language_labels, language_values, "Language mix · original repos", theme),
        )
        write_svg(output / f"card-stats-{theme_name}.svg", render_stats(data, theme))
        write_svg(output / f"languages-{theme_name}.svg", render_language_bars(data, theme))
        write_svg(output / f"achievements-{theme_name}.svg", render_achievements(data, len(projects), theme))
        write_svg(output / f"achievements-mobile-{theme_name}.svg", render_achievements_mobile(data, len(projects), theme))
        write_svg(output / f"infrastructure-banner-{theme_name}.svg", render_infrastructure(theme))
        write_svg(output / f"infrastructure-banner-mobile-{theme_name}.svg", render_infrastructure_mobile(theme))
        write_svg(output / f"automation-loop-{theme_name}.svg", render_automation_loop(theme))
        write_svg(output / f"automation-loop-mobile-{theme_name}.svg", render_automation_loop_mobile(theme))
        for project in projects:
            repo = repo_lookup.get(project["repo"].casefold(), {})
            safe_name = project["repo"].casefold().replace("_", "-")
            write_svg(output / f"project-{safe_name}-{theme_name}.svg", render_project_card(project, repo, theme))

    render_isocalendar(data_path, output / "metrics.isocalendar.svg", "dark")
    render_isocalendar(data_path, output / "metrics.isocalendar-light.svg", "light")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=USERNAME)
    parser.add_argument("--data", type=Path, default=Path("assets/profile-data.json"))
    parser.add_argument("--skills", type=Path, default=Path("assets/skills.json"))
    parser.add_argument("--projects", type=Path, default=Path("assets/projects.json"))
    parser.add_argument("--output", type=Path, default=Path("assets"))
    parser.add_argument("--fetch", action="store_true", help="Refresh the public data snapshot before rendering")
    arguments = parser.parse_args()

    if arguments.fetch:
        try:
            data = collect_public_data(arguments.username)
            arguments.data.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")
        except Exception as error:
            if not arguments.data.exists():
                raise
            print(f"warning: refresh failed; rendering the last known-good snapshot: {error}")
            data = json.loads(arguments.data.read_text(encoding="utf-8"))
    else:
        data = json.loads(arguments.data.read_text(encoding="utf-8"))
    render_all(data, arguments.data, arguments.skills, arguments.projects, arguments.output)


if __name__ == "__main__":
    main()
