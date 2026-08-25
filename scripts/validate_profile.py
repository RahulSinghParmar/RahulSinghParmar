"""Validate the profile README and its repository-hosted assets before publish."""

from __future__ import annotations

import json
import py_compile
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSETS = ROOT / "assets"
PRIVATE_SOURCES = {"photo.png", "photome.png", "portrait-cutout-source.png"}
LEGACY_PATHS = {"index.html", "assets/banner.png", "assets/header.png"}
REQUIRED_PROJECT_FIELDS = {"repo", "title", "description", "impact", "stack"}


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path, errors: list[str]) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"invalid JSON: {path.relative_to(ROOT)} ({error})")
        return {}


def local_asset_references(readme: str) -> list[str]:
    html_references = re.findall(r'(?:src|srcset)="([^"]+)"', readme)
    markdown_references = re.findall(r'!\[[^\]]*\]\(([^)\s]+)', readme)
    references: list[str] = []
    for reference in html_references + markdown_references:
        if not urlsplit(reference).scheme and not reference.startswith("#"):
            references.append(reference.split("?", 1)[0].split("#", 1)[0])
    return references


def tracked_files(errors: list[str]) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        errors.append(f"unable to inspect tracked files ({error})")
        return set()
    return {item for item in result.stdout.decode("utf-8").split("\0") if item}


def main() -> int:
    errors: list[str] = []
    readme = README.read_text(encoding="utf-8")

    check("Team Lead Network Engineer" in readme, "README is missing the recruiter headline", errors)
    check(readme.count("<picture>") == readme.count("</picture>"), "README has an unbalanced <picture> block", errors)
    for block in re.findall(r"<picture>.*?</picture>", readme, flags=re.DOTALL):
        check("<img " in block and "alt=" in block, "every <picture> needs an <img> fallback with alt text", errors)
    for image in re.findall(r"<img\b[^>]*>", readme):
        check("alt=" in image, f"image is missing alt text: {image[:100]}", errors)

    local_references = local_asset_references(readme)
    for reference in local_references:
        target = (README.parent / reference).resolve()
        check(target.is_relative_to(ROOT), f"local reference escapes the repository: {reference}", errors)
        check(target.is_file(), f"missing local README asset: {reference}", errors)

    svg_files = sorted(ASSETS.glob("*.svg"))
    for svg in svg_files:
        try:
            ET.parse(svg)
        except ET.ParseError as error:
            errors.append(f"invalid SVG XML: {svg.relative_to(ROOT)} ({error})")

    for theme in ("light", "dark"):
        for stem in (
            "portrait",
            "radar-skills",
            "radar-languages",
            "card-stats",
            "languages",
            "achievements",
            "infrastructure-banner",
            "automation-loop",
        ):
            check((ASSETS / f"{stem}-{theme}.svg").is_file(), f"missing theme asset: {stem}-{theme}.svg", errors)
        for stem in ("achievements-mobile", "infrastructure-banner-mobile", "automation-loop-mobile"):
            check((ASSETS / f"{stem}-{theme}.svg").is_file(), f"missing mobile theme asset: {stem}-{theme}.svg", errors)

    portrait = (ASSETS / "portrait-light.svg").read_text(encoding="utf-8")
    check("portrait-reveal" in portrait, "portrait entrance animation is missing", errors)
    check("<rect" not in portrait, "portrait must not contain a background rectangle", errors)

    projects = load_json(ASSETS / "projects.json", errors)
    if isinstance(projects, list):
        repositories: list[str] = []
        for index, project in enumerate(projects):
            check(isinstance(project, dict), f"project {index} must be an object", errors)
            if not isinstance(project, dict):
                continue
            check(REQUIRED_PROJECT_FIELDS <= project.keys(), f"project {index} is missing required fields", errors)
            check(isinstance(project.get("stack"), list) and bool(project.get("stack")), f"project {index} needs a non-empty stack", errors)
            repositories.append(str(project.get("repo", "")).casefold())
        check(len(repositories) == len(set(repositories)), "project repository names must be unique", errors)
    else:
        errors.append("assets/projects.json must contain a list")

    skills = load_json(ASSETS / "skills.json", errors)
    if isinstance(skills, dict) and isinstance(skills.get("skills"), list):
        labels: list[str] = []
        for skill in skills["skills"]:
            check(isinstance(skill, dict), "each skill must be an object", errors)
            if not isinstance(skill, dict):
                continue
            value = skill.get("value")
            check(isinstance(value, (int, float)) and 0 <= value <= 100, f"invalid skill value: {skill}", errors)
            labels.append(str(skill.get("label", "")).casefold())
        check(len(labels) == len(set(labels)), "skill labels must be unique", errors)
    else:
        errors.append("assets/skills.json must contain a skills list")

    profile_data = load_json(ASSETS / "profile-data.json", errors)
    if isinstance(profile_data, dict):
        for key in ("user", "repos", "languages", "contributions"):
            check(key in profile_data, f"profile data is missing {key}", errors)
        contributions = profile_data.get("contributions", [])
        check(isinstance(contributions, list) and bool(contributions), "profile contributions must not be empty", errors)
        if isinstance(contributions, list) and contributions:
            dates = [str(item.get("date", "")) for item in contributions if isinstance(item, dict)]
            check(dates == sorted(dates), "profile contributions must be sorted by date", errors)

    for script in sorted((ROOT / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as error:
            errors.append(f"Python compilation failed: {script.relative_to(ROOT)} ({error.msg})")

    tracked = tracked_files(errors)
    for private_source in PRIVATE_SOURCES:
        check(private_source not in tracked, f"private portrait source is tracked: {private_source}", errors)
    for legacy_path in LEGACY_PATHS:
        check(not (ROOT / legacy_path).exists(), f"obsolete legacy file still exists: {legacy_path}", errors)
    check(not (ROOT / "rahulsinghparmar_files").exists(), "obsolete website export still exists", errors)

    if errors:
        print("Profile validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Profile validation passed: {len(local_references)} local references, "
        f"{len(svg_files)} SVG assets, {len(projects) if isinstance(projects, list) else 0} featured projects."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
