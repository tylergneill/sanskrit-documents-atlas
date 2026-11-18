"""The site's change log (`/whatisnew` and its yearly archives) -> one row per event.

`https://sanskritdocuments.org/whatisnew` logs additions and updates, one
`<LI>` each, since April 2010. The current page holds the current year; the
rest are separate pages it links from its footer (`whatisnew_2025.php`, ...,
`whatisnew_2020back.php`). `make fetch-whatisnew` caches them all under
`data/metadata_cache/whatisnew/`; this stage reads that cache, with no network,
and writes `data/whatisnew_events.jsonl`:

    {"doc_id": "doc_shiva/shivastutiH18", "verb": "added", "date": "2026-11-04",
     "page": "whatisnew"}

## What an event proves, and what it does not

**A document's first logged event is an "existed by" date**, the same kind
of evidence as presence in the 2020 snapshot, and it combines with that by
taking the earlier date (`build_changelog --attest-events`). It is not an
arrival date, because the log is pruned:

  - deleting a document deletes its log history;
  - a moved or renamed document keeps only its events under the new path,
    so its `added` line is lost (`shivastutiHdaksha`, moved
    `doc_ganesha` -> `doc_shiva`, shows only a 2026 `updated`);
  - some repeat `updated` lines are hand-tidied away.

Measured against the 2020 snapshot's own copy of the page: today's pages drop
54 of 5,975 entries for that span, add none, and change no surviving date. So
the log errs in one direction only -- toward late -- the same as `Latest
update`, and a `min` across sources is safe.

**It is not a full record of edits either**: over Aug -> Nov 2026 it named 52
of 310 text changes, all of them real (notes/scratch/whatisnew.md). Use it for
dating and for refresh hints, never as proof that an unlogged document is
unchanged.

## Three entry shapes

    Files X.* added <a href='/doc_shiva/X.html' ...>title</a> on 2026-11-04
    Files X.* updated <a href='/doc_giitaa/X.html' ...>title</a> on 07 Nov 2017
    Files X.* are added in folder <a href=/deities_misc/>doc_deities_misc</a> on Apr 25, 2010

The first is every entry since 2017; the last two are the 2010-2017 forms,
where the folder is the link TEXT, not the href. A handful of hrefs carry a
stray space (`/doc_ deities_misc/`), and the 2020 copy appends `?lang=sa`.

Run: python -m pipeline.parse_whatisnew
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from pipeline.config import (WHATISNEW_CACHE_DIR, WHATISNEW_EVENTS_PATH,
                             dump_2020_root)
from pipeline.parse_index import SITE_BASE, strip_nav

WHATISNEW_URL = f"{SITE_BASE}/whatisnew"

# The archive pages, as the main page's footer links them: `whatisnew_2025.php`
# and so on. Discovered rather than listed, so the year rollover (2026 moving
# out to its own page) needs no code change.
ARCHIVE_RE = re.compile(r"""href=["']?\.?/?(whatisnew_[\w-]+\.php)""", re.I)

ITEM_RE = re.compile(r"<LI>(.*?)(?=<LI>|</UL>|</LI>)", re.S | re.I)
HEAD_RE = re.compile(r"\s*Files?\s+(\S+?)\.\*?\s+(?:are\s+)?(added|updated)\b", re.I)
HREF_RE = re.compile(r"""<a\s[^>]*?href=(["']?)([^"'>]*?)\1[\s>]""", re.I)
FOLDER_TEXT_RE = re.compile(r">\s*(doc_\w+)\s*</a>", re.I)
TAG_RE = re.compile(r"<[^>]+>")

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DMY_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
MDY_RE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b")


def archive_page_links(page: str) -> list[str]:
    """The main page's footer -> absolute URLs of its yearly archive pages."""
    seen = []
    for name in ARCHIVE_RE.findall(page):
        url = f"{SITE_BASE}/{name}"
        if url not in seen:
            seen.append(url)
    return seen


def page_slug(url: str) -> str:
    """`.../whatisnew_2025.php` -> `whatisnew_2025`; the cache file stem."""
    return url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".php")


def _month(name: str) -> int | None:
    return MONTHS.get(name[:3].lower())


def parse_date(text: str) -> str | None:
    """The text after an entry's last ` on ` -> `YYYY-MM-DD`, or None."""
    m = ISO_RE.search(text)
    if m:
        return "-".join(m.groups())
    m = DMY_RE.search(text)
    if m and _month(m.group(2)):
        return f"{m.group(3)}-{_month(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = MDY_RE.search(text)
    if m and _month(m.group(1)):
        return f"{m.group(3)}-{_month(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def _doc_path(href: str) -> str | None:
    """An entry's href -> `doc_x/stem`, or None if it names no document."""
    href = re.sub(r"\s+", "", href).split("?")[0]
    if href.startswith(SITE_BASE):
        href = href[len(SITE_BASE):]
    m = re.match(r"/(doc_[^/]+)/(.+?)\.html$", href)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def parse_events(page: str) -> tuple[list[dict], list[str]]:
    """One change-log page -> (events, entries that could not be read)."""
    events, unread = [], []
    for item in ITEM_RE.findall(strip_nav(page)):
        flat = re.sub(r"\s+", " ", item)
        head = HEAD_RE.match(flat)
        if not head:
            continue
        stem, verb = head.group(1), head.group(2).lower()
        doc_id = None
        href = HREF_RE.search(flat)
        if href:
            doc_id = _doc_path(href.group(2))
        if doc_id is None:
            folder = FOLDER_TEXT_RE.search(flat)
            if folder:
                doc_id = f"{folder.group(1)}/{stem}"
        tail = TAG_RE.sub(" ", flat)
        on = tail.rfind(" on ")
        date = parse_date(tail[on:]) if on >= 0 else None
        if doc_id is None or date is None:
            unread.append(flat[:200])
            continue
        events.append({"doc_id": doc_id, "verb": verb, "date": date})
    return events, unread


def id_resolver(doc_ids: set[str]):
    """A log doc_id -> the corpus doc_id it names, or None.

    Exact match first, then a unique case-insensitive one: the log's hrefs are
    hand-typed and differ in case from the served path now and then. A
    lowercased id shared by two documents (the case-clash pairs) is left
    unresolved rather than guessed.
    """
    by_lower: dict[str, list[str]] = {}
    for doc_id in doc_ids:
        by_lower.setdefault(doc_id.lower(), []).append(doc_id)

    def resolve(log_id: str) -> str | None:
        if log_id in doc_ids:
            return log_id
        matches = by_lower.get(log_id.lower(), [])
        return matches[0] if len(matches) == 1 else None

    return resolve


def collect(cache: Path, dump_copy: Path | None) -> tuple[list[dict], Counter]:
    """Every cached page, plus the 2020 snapshot's copy if given, deduplicated."""
    sources = sorted(cache.glob("*.html")) if cache.is_dir() else []
    if dump_copy is not None and dump_copy.exists():
        sources.append(dump_copy)
    seen: dict[tuple, dict] = {}
    report: Counter = Counter()
    for path in sources:
        label = "2020-snapshot" if path == dump_copy else path.stem
        events, unread = parse_events(path.read_text(encoding="utf-8", errors="replace"))
        report[f"{label} events"] = len(events)
        report[f"{label} unread"] = len(unread)
        for e in events:
            key = (e["doc_id"], e["verb"], e["date"])
            # Prefer the live pages' attribution when both carry an event.
            seen.setdefault(key, {**e, "page": label})
    rows = sorted(seen.values(), key=lambda e: (e["date"], e["doc_id"], e["verb"]))
    return rows, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache", type=Path, default=WHATISNEW_CACHE_DIR)
    parser.add_argument("--out", type=Path, default=WHATISNEW_EVENTS_PATH)
    parser.add_argument("--no-dump", action="store_true",
                        help="skip the 2020 snapshot's copy of the page. It "
                             "keeps ~50 entries the live log has since pruned, "
                             "so it can only make dates earlier.")
    args = parser.parse_args()

    if not args.cache.is_dir() or not any(args.cache.glob("*.html")):
        raise SystemExit(f"no cached change-log pages in {args.cache}; "
                         "run `make fetch-whatisnew` first.")
    dump_copy = None if args.no_dump else dump_2020_root() / "whatisnew" / "index.html"
    rows, report = collect(args.cache, dump_copy)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    for key in sorted(report):
        print(f"  {key:28} {report[key]:6}")
    verbs = Counter(r["verb"] for r in rows)
    print(f"events:    {len(rows)} distinct ({verbs['added']} added, "
          f"{verbs['updated']} updated) naming {len({r['doc_id'] for r in rows})} doc_ids")
    print(f"range:     {rows[0]['date']} -> {rows[-1]['date']}" if rows else "range: none")
    print(f"wrote:     {args.out}")


if __name__ == "__main__":
    main()
