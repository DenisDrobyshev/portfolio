#!/usr/bin/env python3
"""Refresh publications.html and publications-ru.html from Zenodo.

Queries Zenodo for records by the author, keeps only the ones where a creator
carries ORCID (or, failing that, a name starting with NAME), and rewrites the
block delimited by PUBLICATIONS:START / PUBLICATIONS:END. Run daily by
.github/workflows/update-publications.yml.

View and download counts are not written here: they change every day and would
produce a commit per day. assets/publications.js fetches them in the browser.
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
MAX_TAGS = 4

RU_MONTHS = (
    "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
)
TYPES = {
    "en": {"preprint": "Preprint", "publication": "Paper", "journal article": "Article",
           "conference paper": "Conference paper", "report": "Report", "software": "Software",
           "dataset": "Dataset", "book": "Book"},
    "ru": {"preprint": "Препринт", "publication": "Статья", "journal article": "Статья",
           "conference paper": "Доклад", "report": "Отчёт", "software": "Код",
           "dataset": "Данные", "book": "Книга"},
}
TEXT = {
    "en": {"papers": "papers", "coauthors": "co-authors", "downloads": "downloads",
           "views": "views", "abstract": "Abstract", "cite": "Cite", "copy_doi": "Copy DOI"},
    "ru": {"papers": "работ", "coauthors": "соавторов", "downloads": "скачиваний",
           "views": "просмотров", "abstract": "Аннотация", "cite": "Цитировать",
           "copy_doi": "Скопировать DOI"},
}


def clean(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def paragraphs(raw: str) -> list[str]:
    parts = re.split(r"</p\s*>|<br\s*/?>", raw or "", flags=re.I)
    return [text for text in (clean(part) for part in parts) if text]


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
        creators = meta.get("creators", [])
        if not any(is_mine(c) for c in creators):
            continue  # free-text search can match other people
        try:
            published = datetime.strptime(meta["publication_date"], "%Y-%m-%d")
        except (KeyError, ValueError):
            continue
        rtype = meta.get("resource_type") or {}
        pdf = next((f["key"] for f in hit.get("files", [])
                    if f.get("key", "").lower().endswith(".pdf")), None)
        record_id = hit.get("id")
        records.append({
            "id": record_id,
            "title": meta.get("title", "").strip(),
            "date": published,
            "type": (rtype.get("subtype") or rtype.get("type") or "").strip().lower(),
            "doi": hit.get("doi", ""),
            "abstract": paragraphs(meta.get("description", "")),
            "keywords": [k.strip() for k in meta.get("keywords", []) if k.strip()][:MAX_TAGS],
            "url": (hit.get("links") or {}).get("self_html")
                   or f"https://zenodo.org/records/{record_id}",
            "pdf": f"https://zenodo.org/records/{record_id}/files/"
                   f"{urllib.parse.quote(pdf)}?download=1" if pdf else None,
            "creators": [(c.get("name", "").strip(), is_mine(c)) for c in creators],
        })
    records.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    return records


def short_name(name: str) -> str:
    """'Drobyshev, Denis O.' -> 'Drobyshev D. O.'"""
    if "," not in name:
        return name
    last, first = (part.strip() for part in name.split(",", 1))
    initials = " ".join(f"{p[0]}." for p in re.split(r"[\s.]+", first) if p)
    return f"{last} {initials}".strip()


def when(moment: datetime, lang: str) -> str:
    if lang == "ru":
        return f"{moment.day} {RU_MONTHS[moment.month - 1]} {moment.year}"
    return f"{moment.day} {moment.strftime('%b')} {moment.year}"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_record(record: dict, number: int, lang: str) -> str:
    t = TEXT[lang]
    kind = TYPES[lang].get(record["type"], record["type"].capitalize() or TYPES[lang]["preprint"])
    authors = ", ".join(
        f'<span class="pub-me">{esc(short_name(n))}</span>' if mine else esc(short_name(n))
        for n, mine in record["creators"]
    )
    tags = "".join(f"<li>{esc(k)}</li>" for k in record["keywords"])
    tags_html = f'\n        <ul class="pub-tags">{tags}</ul>' if tags else ""
    pdf = (f'\n          <a class="pub-btn pub-btn-primary" href="{esc(record["pdf"])}">PDF</a>'
           if record["pdf"] else "")
    doi = record["doi"]
    doi_html = (
        f'\n          <a class="pub-btn" href="https://doi.org/{esc(doi)}">DOI</a>'
        f'\n          <button class="pub-doi" type="button" data-copy="{esc(doi)}" '
        f'title="{esc(t["copy_doi"])}">{esc(doi)}</button>'
    ) if doi else ""
    abstract = "".join(f"<p>{esc(text)}</p>" for text in record["abstract"])
    bib_authors = " and ".join(n for n, _ in record["creators"])
    return f'''    <li class="pub" id="zenodo-{record["id"]}" data-id="{record["id"]}" data-year="{record["date"].year}" data-authors="{esc(bib_authors)}">
      <div class="pub-index" aria-hidden="true">{number:02d}</div>
      <div class="pub-body">
        <div class="pub-top">
          <span class="pub-type">{esc(kind)}</span>
          <time datetime="{record["date"]:%Y-%m-%d}">{when(record["date"], lang)}</time>
          <span class="pub-stats" hidden></span>
        </div>
        <h2 class="pub-title"><a href="{esc(record["url"])}">{esc(record["title"])}</a></h2>
        <p class="pub-authors">{authors}</p>
        <div class="pub-abstract">{abstract}</div>{tags_html}
        <div class="pub-actions">{pdf}{doi_html}
          <button class="pub-btn pub-cite" type="button">{esc(t["cite"])}</button>
          <button class="pub-btn pub-more" type="button" aria-expanded="false" hidden>{esc(t["abstract"])}</button>
        </div>
      </div>
    </li>'''


def render(records: list[dict], lang: str) -> str:
    t = TEXT[lang]
    coauthors = {n for r in records for n, mine in r["creators"] if not mine}
    summary = f'''  <div class="pub-summary">
    <div class="pub-stat"><span class="pub-stat-num">{len(records)}</span><span class="pub-stat-label">{t["papers"]}</span></div>
    <div class="pub-stat"><span class="pub-stat-num">{len(coauthors)}</span><span class="pub-stat-label">{t["coauthors"]}</span></div>
    <div class="pub-stat" data-total="downloads" hidden><span class="pub-stat-num"></span><span class="pub-stat-label">{t["downloads"]}</span></div>
    <div class="pub-stat" data-total="views" hidden><span class="pub-stat-num"></span><span class="pub-stat-label">{t["views"]}</span></div>
    <div class="pub-profiles">
      <a href="https://orcid.org/{ORCID}">ORCID</a>
      <a href="https://zenodo.org/search?q=metadata.creators.person_or_org.identifiers.identifier%3A%22{ORCID}%22">Zenodo</a>
    </div>
  </div>'''
    total = len(records)
    rows = "\n\n".join(render_record(r, total - i, lang) for i, r in enumerate(records))
    return f'{summary}\n\n  <ol class="pub-list">\n{rows}\n  </ol>'


def rewrite(path: Path, body: str) -> bool:
    text = path.read_text(encoding="utf-8")
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not block.search(text):
        sys.exit(f"{path.name}: markers not found")
    updated = block.sub(lambda _: f"{START}\n{body}\n  {END}", text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
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
