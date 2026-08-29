#!/usr/bin/env python3
"""Refresh publications.html and publications-ru.html from Zenodo.

Queries Zenodo for records authored by AUTHOR, keeps only the ones where that
name really appears among the creators, and rewrites the block delimited by
PUBLICATIONS:START / PUBLICATIONS:END. Run daily by
.github/workflows/update-publications.yml.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

AUTHOR = "Drobyshev, Denis O."
API = "https://zenodo.org/api/records"
START = "<!-- PUBLICATIONS:START -->"
END = "<!-- PUBLICATIONS:END -->"
ROOT = Path(__file__).resolve().parent.parent

RU_MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
TYPES_RU = {
    "preprint": "препринт", "journal article": "статья", "conference paper": "доклад",
    "report": "отчёт", "software": "код", "dataset": "данные", "book": "книга",
}


def strip_html(raw: str, limit: int = 230) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:") + "…"


def fetch() -> list[dict]:
    query = urllib.parse.urlencode({"q": f'"{AUTHOR}"', "size": 25, "sort": "newest"})
    request = urllib.request.Request(f"{API}?{query}")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "denisdrobyshev.github.io publications")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    records = []
    for hit in payload.get("hits", {}).get("hits", []):
        meta = hit.get("metadata", {})
        creators = [c.get("name", "") for c in meta.get("creators", [])]
        if AUTHOR not in creators:  # free-text search can match other people
            continue
        try:
            published = datetime.strptime(meta["publication_date"], "%Y-%m-%d")
        except (KeyError, ValueError):
            continue
        records.append({
            "title": meta.get("title", "").strip(),
            "date": published,
            "type": (meta.get("resource_type") or {}).get("title", "").strip(),
            "doi": hit.get("doi", ""),
            "summary": strip_html(meta.get("description", "")),
            "url": (hit.get("links") or {}).get("self_html")
                   or f"https://zenodo.org/records/{hit.get('id')}",
            "creators": creators,
        })
    records.sort(key=lambda r: r["date"], reverse=True)
    return records


def when(moment: datetime, lang: str) -> str:
    if lang == "ru":
        return f"{moment.day} {RU_MONTHS[moment.month - 1]} {moment.year}"
    return moment.strftime("%d %B %Y").lstrip("0")


def kind(name: str, lang: str) -> str:
    low = name.lower()
    return TYPES_RU.get(low, low or "препринт") if lang == "ru" else (low or "preprint")


def render(records: list[dict], lang: str) -> str:
    rows = []
    for record in records:
        meta = f'{when(record["date"], lang)} · doi {html.escape(record["doi"])}'
        if len(record["creators"]) > 1:
            meta = html.escape(", ".join(record["creators"])) + " · " + meta
        rows.append(
            f'''    <li class="post-item">
      <h3 class="post-item-title"><a href="{html.escape(record["url"])}">{html.escape(record["title"])}</a></h3>
      <div class="post-item-meta">{meta} <span class="reading-time">{html.escape(kind(record["type"], lang))}</span></div>
      <p class="post-item-excerpt">{html.escape(record["summary"])}</p>
    </li>'''
        )
    return "\n\n".join(rows)


def rewrite(path: Path, body: str) -> bool:
    text = path.read_text(encoding="utf-8")
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not block.search(text):
        sys.exit(f"{path.name}: markers not found")
    updated = block.sub(lambda _: f"{START}\n{body}\n  {END}", text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    records = fetch()
    if not records:
        sys.exit("Zenodo returned nothing — refusing to blank the list")
    changed = False
    for name, lang in (("publications.html", "en"), ("publications-ru.html", "ru")):
        path = ROOT / name
        if path.exists() and rewrite(path, render(records, lang)):
            changed = True
            print(f"updated {name}")
    print(f"{len(records)} publications" if changed else "no change")


if __name__ == "__main__":
    main()
