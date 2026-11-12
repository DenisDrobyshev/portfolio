#!/usr/bin/env python3
"""Refresh publications.html and publications-ru.html from Zenodo.

Queries Zenodo for records by the author, keeps only the ones where a creator
carries ORCID (or, failing that, a name starting with NAME), and rewrites the block delimited by
PUBLICATIONS:START / PUBLICATIONS:END. Run daily by
.github/workflows/update-publications.yml.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ORCID = "0009-0000-0976-1197"
NAME = "Drobyshev, Denis"  # matches "Drobyshev, Denis" and "Drobyshev, Denis O."
PAGE = 25  # anonymous API rejects bigger pages
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


def get(url: str) -> dict:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "denisdrobyshev.github.io publications")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == 3:
                raise
        except urllib.error.URLError:
            if attempt == 3:
                raise
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("unreachable")


def is_mine(creator: dict) -> bool:
    if creator.get("orcid"):
        return creator["orcid"] == ORCID
    return creator.get("name", "").startswith(NAME)


def fetch() -> list[dict]:
    hits, page = [], 1
    while True:
        query = urllib.parse.urlencode(
            {"q": f'"{NAME}"', "size": PAGE, "page": page, "sort": "newest"})
        payload = get(f"{API}?{query}")
        batch = payload.get("hits", {}).get("hits", [])
        hits.extend(batch)
        if len(batch) < PAGE or page >= 20:
            break
        page += 1

    records = []
    seen = set()
    for hit in hits:
        if hit.get("id") in seen:
            continue
        seen.add(hit.get("id"))
        meta = hit.get("metadata", {})
        if not any(is_mine(c) for c in meta.get("creators", [])):
            continue  # free-text search can match other people
        creators = [c.get("name", "") for c in meta.get("creators", [])]
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
