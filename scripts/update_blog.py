"""Refresh the README blog list from Rahul's Hashnode RSS feed."""

from __future__ import annotations

import argparse
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"


def fetch(url: str, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "RahulSinghParmar-profile-assets"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to fetch {url}") from last_error


def markdown_safe(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]")


def update(readme: Path, feed_url: str, limit: int, canonical_base: str) -> None:
    root = ET.fromstring(fetch(feed_url))
    posts: list[tuple[str, str]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "Untitled").strip()
        link = (item.findtext("link") or "").strip()
        if link:
            parsed = urllib.parse.urlparse(link)
            if parsed.hostname in {"rahulsinghparmar.me", "www.rahulsinghparmar.me"}:
                link = f"{canonical_base.rstrip('/')}{parsed.path}"
            posts.append((title, link))
        if len(posts) == limit:
            break
    if not posts:
        raise RuntimeError("The RSS feed returned no posts; README left unchanged")

    text = readme.read_text(encoding="utf-8")
    before, separator, remainder = text.partition(START)
    if not separator:
        raise RuntimeError(f"Missing marker: {START}")
    _, separator, after = remainder.partition(END)
    if not separator:
        raise RuntimeError(f"Missing marker: {END}")
    entries = "\n".join(f"- [{markdown_safe(title)}]({link})" for title, link in posts)
    readme.write_text(f"{before}{START}\n{entries}\n{END}{after}", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--feed", default="https://rahulsinghparmar.hashnode.dev/rss.xml")
    parser.add_argument("--canonical-base", default="https://rahulsinghparmar.hashnode.dev")
    parser.add_argument("--limit", type=int, default=5)
    arguments = parser.parse_args()
    update(arguments.readme, arguments.feed, arguments.limit, arguments.canonical_base)


if __name__ == "__main__":
    main()
