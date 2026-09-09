"""Stage 1d: scanned sources linked from the listing and location pages.

Beside each document the site often prints a parenthetical of external links --
`(Scans 1, 2, 3, Hindi 1, 2, Thesis, Kalyan 1, 2)` -- pointing at archive.org
items, PDFs it hosts under `/scannedbooks/`, and PDFs on third-party sites.
Somewhere in there is the printed book the etext corresponds to.

**Nothing on the page asserts that correspondence.** The site never says which
scan an etext was encoded from, and the same volume is cited by every text it
contains: one Shiva-purana scan is attached to dozens of stotras excerpted from
it. So this stage does NOT emit "the source of this etext". It emits *scanned
sources the site links*, under a rule chosen to be conservative rather than
complete.

The rule, arrived at by reading the pages (see `notes/site-structure.md`):

1. **First parenthetical link only.** Later links in the same entry are
   translations, commentaries, videos, cross-references to other etexts, and
   author collections. Only the first has a good chance of being the text
   itself, so the rest are dropped wholesale rather than sifted.
2. **The label must be a scan-ish keyword** -- scan/scanned/scanned book/
   manuscript/text, in any case, optionally `#`-prefixed -- or a bare numeral,
   which is how the site writes the second and later items of a labelled run.
3. **The target must be a PDF**: an archive.org item, a `/scannedbooks/` file,
   or a `.pdf` anywhere else. A blogspot post labelled "scanned book" is not.

Both halves are written out. `scans.jsonl` is what survives; `scans_rejected.
jsonl` is everything the rule dropped, with a `reason`, because the rule is
provisional and the rejects are where the next refinement will come from --
notably ~300 PDFs whose label is a book title rather than a keyword.

Run: python -m pipeline.parse_scans
"""

import argparse
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

from pipeline.config import (LISTING_CACHE_DIR, LOCATION_CACHE_DIR,
                             SCANS_PATH, SCANS_REJECTED_PATH)
from pipeline.parse_index import strip_nav

LI = re.compile(r"<li\b.*?</li>", re.S | re.I)
ANCHOR = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S | re.I)
TAG = re.compile(r"<[^>]+>")

# The document an entry is about: the docpage link carrying a `title=`. Entries
# that pair a stotram with its namavali link both, and only the first is titled.
TITLED = re.compile(
    r'<a\s+href=["\']/?(doc_[a-zA-Z0-9_]+)/([^/"\']+)\.html["\'][^>]*title=', re.I)
DOCPAGE = re.compile(r'/?(doc_[a-zA-Z0-9_]+)/([^/"\']+)\.html', re.I)

# A label is the word-run immediately before a link. It governs the whole
# comma-separated run that follows -- `(Scans 1, 2, 3)` labels only the first,
# and 2 and 3 inherit it -- so it is carried forward until something replaces it.
LABEL = re.compile(r"([A-Za-z][A-Za-z0-9 /&.'-]{0,28})\s*$")

# A keyword ANYWHERE in the label, not the whole label. The site compounds
# freely -- `Scan, Hindi`, `Tamil Scan`, `Scan and vyAkhyA`, `DLI scanned`,
# `scanned copy`, and the typo `Temil Scan` -- and an anchored match dropped 58
# links whose label plainly says scan. `Temil` is why this matches the keyword
# rather than trying to validate the rest of the string.
KEEP_LABEL = re.compile(
    r"\b(scans?|scanned|scanned\s*books?|manuscripts?|texts?)\b", re.I)

# `Sanskrit` alone is kept: it names the language of the *edition*, and those
# targets are ordinary page-anchored scans (DLI volumes, the Rajasthan series)
# indistinguishable from the ones labelled `Scan`. Other language names are NOT
# kept -- `Hindi`, `Tamil`, `English` on their own mark a translation, which is
# a different text rather than a witness to this one.
KEEP_SANSKRIT = re.compile(r"^#?\s*sanskrit$", re.I)

# What a label must NOT contain, checked anywhere in the string for the same
# reason KEEP_LABEL is: the site compounds. `Tamil-English Translation`,
# `Hindi vyAkhyA`, `Sanskrit-Hindi TIkA commentary` and `Word by Word
# Hindi-Sanskrit` all name a translation or commentary -- a different text --
# and all escape a whole-string match.
#
# `Sanskrit` is deliberately absent here: it survives via KEEP_SANSKRIT, and
# only when it is the WHOLE label. `Sanskrit-Hindi TIkA` is excluded, correctly.
REJECT_LABEL = re.compile(
    r"(hindi|tamil|telugu|kannada|english|malayalam|marathi|bengali|gujarati"
    r"|oriya|punjabi|assamese|nepali|urdu"
    r"|translat|meaning|commentar|t[iI]k[aA]|TippaN|vy[aA]khy[aA]"
    r"|audio|video|thesis|paintings?|wiki)", re.I)

# Everything else with a PDF target is admitted. Most of these labels name the
# ANTHOLOGY the text sits in -- `stotram[aA]l[aA]`, `stotr[aA]disangraha`,
# `pushti margiya stotraratn[aA]kara`, `VSM 2` -- which is why they do not
# resemble the document's own title (median similarity 0.26 against the doc_id
# stem, so matching label to title was tried and abandoned). The site is naming
# the collection to look in, which is a real witness, just a coarse one.

NUMERAL = re.compile(r"^#?\s*\d+$")

# archive.org in both spellings: the browsable paths, and the ia###.us storage
# nodes that serve `/N/items/<item>/file.pdf` directly.
ARCHIVE_PATH = re.compile(
    r"archive\.org/(?:details|stream|download)/([^/?#\"']+)", re.I)
ARCHIVE_NODE = re.compile(r"ia\d+\.us\.archive\.org/\d+/items/([^/?#\"']+)", re.I)
PDF_SUFFIX = re.compile(r"\.pdf(\?|#|$)", re.I)


def plain(fragment: str) -> str:
    """Markup -> the text a reader sees, whitespace collapsed."""
    return re.sub(r"\s+", " ", TAG.sub("", fragment)).strip()


def classify(url: str) -> tuple[str, str]:
    """-> (kind, identifier), or ("", "") when the target is not a PDF.

    `kind` names the hosting corpus rather than the file type, because that is
    what decides how the link is checked and how much it can be trusted:
    archive.org items are stable and dereferenceable, `/scannedbooks/` is the
    site's own, and third-party PDFs are neither.
    """
    match = ARCHIVE_NODE.search(url) or ARCHIVE_PATH.search(url)
    if match:
        return "archive", match.group(1)
    if PDF_SUFFIX.search(url):
        if "scannedbooks" in url.lower():
            return "scannedbooks", url.rsplit("/", 1)[-1]
        host = url.split("/")[2] if "//" in url else ""
        return "third-party", host
    return "", ""


def stem(url: str) -> str:
    """Collapse a link to the thing it identifies.

    Page-anchored archive.org links (`/page/n170/mode/1up`) differ per document
    while naming one book, so counting URLs would overcount volumes several
    times over. Everything non-archive stems to itself, minus query and
    fragment.
    """
    match = ARCHIVE_NODE.search(url)
    if match:
        return f"archive.org/details/{match.group(1)}"
    match = ARCHIVE_PATH.search(url)
    if match:
        return re.sub(r"/(?:stream|download)/", "/details/", match.group(0), flags=re.I)
    return url.split("?")[0].split("#")[0]


def owning_doc(entry: str) -> str:
    titled = TITLED.search(entry)
    if titled:
        return f"{titled.group(1)}/{titled.group(2)}"
    any_doc = DOCPAGE.search(entry)
    return f"{any_doc.group(1)}/{any_doc.group(2)}" if any_doc else ""


def external_links(entry: str) -> list[tuple[str, str, str]]:
    """The entry's outbound links, in order, as (label, link_text, url).

    Docpage links are skipped: `.html`/`.itx`/`.pdf` on our own doc_ids are the
    entry's own downloads and its cross-references to sibling etexts, neither of
    which is a scanned source.
    """
    found = []
    carried = None
    cursor = 0
    for match in ANCHOR.finditer(entry):
        between = plain(entry[cursor:match.start()])
        cursor = match.end()
        url, inner = match.group(1), plain(match.group(2))

        if between.strip(" ,|)("):
            label = LABEL.search(between.rstrip(" ("))
            if label and len(label.group(1).strip()) <= 20:
                carried = label.group(1).strip()

        low = url.lower()
        if low.startswith("/doc_") or "sanskritdocuments.org/doc_" in low:
            continue
        if not re.match(r"https?://", url):
            continue

        # A link's own words beat the carried label; a bare numeral has none of
        # its own and inherits.
        own = inner if inner and not re.fullmatch(r"\d+", inner) else None
        found.append((own or carried or "", inner, url))
    return found


def harvest(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    kept: dict[tuple[str, str], dict] = OrderedDict()
    rejected: dict[tuple[str, str], dict] = OrderedDict()

    for path in paths:
        page = strip_nav(path.read_text(encoding="utf-8", errors="replace"))
        for entry in LI.findall(page):
            links = external_links(entry)
            if not links:
                continue
            # Rule 1: the first external link, and nothing after it.
            label, link_text, url = links[0]
            doc_id = owning_doc(entry)
            kind, ident = classify(url)
            # An explicit scan keyword wins outright. `Scan, Hindi` and
            # `Scan Tamil` name a scanned edition that happens to be in Hindi
            # or Tamil, and the site writes plenty of them; rejecting on the
            # language word would drop scans we deliberately added.
            #
            # Failing that, a rejecting word excludes: without a `Scan` to
            # anchor it, `Hindi` or `vyAkhyA` marks a translation or commentary,
            # which is a different text rather than a witness to this one.
            #
            # Anything left is a title -- almost always the anthology the text
            # sits in -- and a title in first position with a PDF target is
            # taken at face value.
            # The numeral clause comes AFTER the reject check, not with the
            # keyword: `(Commentary 1, 2)` writes its first link as "1", and a
            # numeral inherits its group's label -- so it must inherit the
            # group's rejection too, or the label is bypassed entirely.
            if KEEP_LABEL.search(label):
                label_ok = True
            elif REJECT_LABEL.search(label):
                label_ok = False
            else:
                label_ok = bool(KEEP_SANSKRIT.match(label.strip())
                                or NUMERAL.match(link_text or "")
                                or label.strip())

            if label_ok and kind:
                record = {"doc_id": doc_id, "label": label, "link_text": link_text,
                          "kind": kind, "ident": ident, "url": url,
                          "stem": stem(url)}
                kept.setdefault((doc_id, url), record)
            else:
                record = {"doc_id": doc_id, "label": label,
                          "link_text": link_text, "url": url,
                          "reason": "label" if kind else "not-pdf"}
                rejected.setdefault((link_text, url), record)

    return list(kept.values()), list(rejected.values())


def summarize(kept: list[dict]) -> dict:
    """Counts for tree.json. `sources` is the headline: distinct scanned books,
    not link instances -- the same volume cited by 40 stotras counts once."""
    stems = {r["stem"] for r in kept}
    by_kind = Counter(r["kind"] for r in kept)
    kind_stems = {k: len({r["stem"] for r in kept if r["kind"] == k})
                  for k in by_kind}
    return {
        "sources": len(stems),
        "links": len(kept),
        "documents": len({r["doc_id"] for r in kept if r["doc_id"]}),
        "by_kind": kind_stems,
    }


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", type=Path, default=LISTING_CACHE_DIR)
    parser.add_argument("--locations", type=Path, default=LOCATION_CACHE_DIR)
    parser.add_argument("--out", type=Path, default=SCANS_PATH)
    parser.add_argument("--rejected", type=Path, default=SCANS_REJECTED_PATH)
    args = parser.parse_args()

    paths = []
    for directory in (args.listings, args.locations):
        if not directory.exists():
            raise SystemExit(
                f"missing {directory}; run `make fetch-metadata` first.")
        paths.extend(sorted(directory.glob("*.html")))

    kept, rejected = harvest(paths)
    write(args.out, kept)
    write(args.rejected, rejected)

    summary = summarize(kept)
    print(f"pages read:        {len(paths)}")
    print(f"scanned sources:   {summary['sources']} distinct "
          f"(from {summary['links']} links on {summary['documents']} documents)")
    for kind, count in sorted(summary["by_kind"].items(), key=lambda kv: -kv[1]):
        print(f"  {kind:<14} {count}")
    print(f"rejected:          {len(rejected)} "
          f"({Counter(r['reason'] for r in rejected)})")
    print(f"wrote {args.out} and {args.rejected}")


if __name__ == "__main__":
    main()
