"""Stage 1: snapshot docpages -> data/snapshot_inventory.jsonl (one record per text).

Reads `docpage_html_dls/<location>/<name>.html` and pulls each document's own
`<pre class="inf">` block -- the same `% Field : value` table the site renders
at the foot of every text. That block is the primary metadata artifact; the
scrape's `metadata_master.csv` is a derived flattening of it and is not read
here.

Does no network I/O and no body measurement -- `recount_sizes` handles bytes.

Run: python -m pipeline.parse_snapshot [--snapshot PATH] [--report]
"""

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path

from pipeline.categories import build_key as build_category_key
from pipeline.categories import split as split_categories
from pipeline.parse_listings import ALIAS_SURVIVORS
from pipeline.config import (DOCPAGE_DIRNAME, INVENTORY_PATH,
                             LISTING_CACHE_DIR, snapshot_root)

# The `% Field : value` lines inside <pre class="inf">. Values run to EOL and a
# few carry embedded HTML (Indexextra holds <a> links), so this keeps the raw
# string and lets callers decide.
INF_BLOCK_RE = re.compile(
    r'<pre class="inf">(.*?)</pre>', re.DOTALL | re.IGNORECASE
)
INF_LINE_RE = re.compile(r"^%\s*(.+?)\s*:\s*(.*)$")

# The Devanagari title the page shows in its own banner. Preferred over the
# <title>, which carries the romanized form the CSV already has.
SITENAME_RE = re.compile(
    r'<div id="sitename">\s*<span[^>]*>(.*?)</span>', re.DOTALL | re.IGNORECASE
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)

# The disambiguating suffix `fetch_text` appends to case-colliding filenames.
# Mirrors `_case_suffix` there; matched (not imported) so parsing stays
# independent of the fetcher.
CASE_SUFFIX_RE = re.compile(r"~[0-9a-f]{6}$")

# Breadcrumb links double as the download manifest: the .itx source and every
# per-script PDF the site generated. Which scripts exist varies per document,
# so it is recorded rather than assumed.
# Which transliterator the page loads. 9680 pages load Aksharamukha v3; 74 load
# an older Sanscript build (`sanscript-vedic.js` plus a site wrapper, driven by
# jQuery 2.1.1), and 2 metadata-only stubs load neither.
#
# Worth recording because those 74 are not scattered: they are EXACTLY the
# banner-less pages `reconstruct_deva` exists to repair, minus the 2 stubs
# (74 + 2 = 76, checked as an exact nesting -- no legacy page has a banner and
# no banner-less page outside the stubs is on the new stack). So the missing
# `<div id="sitename">` is not sporadic breakage but one un-migrated template,
# and the reconstruction path is really "the legacy template's title".
LEGACY_TRANSLIT_RE = re.compile(r"sanscript-vedic\.js", re.IGNORECASE)

BREADCRUMB_RE = re.compile(
    r'<div id="breadcrumb".*?</div>', re.DOTALL | re.IGNORECASE
)
LINK_RE = re.compile(
    r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE
)

TAG_RE = re.compile(r"<[^>]+>")

# ---------------------------------------------------------------------------
# The Devanagari title of last resort
# ---------------------------------------------------------------------------
# `title_deva` is the ONLY name a document has that can be transliterated into
# the reader's chosen script: `title` is the site's free-text English label
# ("Shri Dayananda Ashtakam : Sanskrit Document"), and feeding that to a
# converter is a silent no-op. 76 of 9756 documents have no <div id="sitename">
# banner at all, and those rendered as English in every script.
#
# All 76 do carry `% itxtitle`, and that field IS real ITRANS -- every one of
# them converts to clean Devanagari with no leftover Latin, checked against the
# 9680 documents that have both. It is not always the same title the banner
# shows (it is often shorter, or differently ordered, so it is a FALLBACK and
# never a preference), but it is a genuine Sanskrit name rather than an English
# description, which is what makes it the right thing to fall back to.
#
# Two caveats, both handled below.
ITX_PAREN_RE = re.compile(r"\s*\(.*$", re.S)

# The site cannot write ITRANS's nasal digraphs: it spells the velar and palatal
# nasals as a plain `n`/`N` where ITRANS wants `N`/`~n`, so conversion yields
# मण्गल for मङ्गल and पन्चकम् for पञ्चकम्. Neither skrutable nor Sanscript can
# help -- the input is genuinely ambiguous ITRANS -- and 24 of the 76 hit it.
#
# The repair is deterministic: Sanskrit phonotactics allow only the homorganic
# nasal before a stop, so before a guttural the nasal IS ङ and before a palatal
# it IS ञ. Verified on the 9680 documents whose real Devanagari is known, where
# the same repair corrected 16 conversions and broke none, every corrected form
# matching the site's own spelling exactly.
ITX_NASAL_FIXES = (
    (re.compile(r"ण्(?=[कखगघ])"), "ङ्"),
    (re.compile(r"न्(?=[चछजझ])"), "ञ्"),
)

# A skrutable bug, not an ambiguity in the source: it reads ITRANS `Ni`/`NI` as
# the vowel RRi/RRI, so `maNi` converts to मऋ rather than मणि and `pramANikA`
# to प्रमाऋका rather than प्रमाणिका. Applied only where the input actually
# contains `N` before `i`/`I`, so a title with a legitimately transliterated
# ऋ is untouched. Verified the same way as the nasal repair: on the documents
# whose real Devanagari is known it corrected 3 and broke none (वाणीवन्दनम्,
# शार्ङ्गपाणिस्तोत्रम्, वज्रपाणिनामाष्टोत्तरशतस्तोत्रम्), each matching the
# site's own spelling. Four of the 76 need it, all `...pramANikA`.
ITX_HAS_NI_RE = re.compile(r"N[iI]")
ITX_VOWEL_N_FIXES = (
    (re.compile(r"ऋ"), "णि"),
    (re.compile(r"ॠ"), "णी"),
)


_translit = None


def reconstruct_deva(itxtitle: str) -> str:
    """`itxtitle` -> Devanagari, or "" if it cannot be converted.

    **Reconstruction, not transliteration.** The conversion asks skrutable to
    read `itxtitle` as ITRANS, but the site's romanization is not ITRANS and
    only resembles it -- `~n`/`~N` never appear, so n/n cannot be written at
    all; `shh` stands for s where ITRANS wants `Sh`, `ksh` for ks. Real ITRANS
    reproduces one of these stems about 3% of the time (see
    notes/site-structure.md). The ITX_*_FIXES below patch the systematic cases,
    but the output remains a best-effort rebuild of a title the page never
    carried -- not the same kind of value as a `title_deva` read off the banner.
    Hence the `title_deva_reconstructed` flag, and hence `audit.field_coverage`
    excludes these from what the source is credited with supplying.

    Uses skrutable, already a dependency (see recount_sizes, which transliterates
    every body with it) -- no new package for 76 documents. Import is lazy for
    the same reason it is there: skrutable is slow to import, and most callers
    of this module never reach this path.
    """
    itx = ITX_PAREN_RE.sub("", (itxtitle or "").strip()).strip()
    if not itx:
        return ""
    global _translit
    if _translit is None:
        from skrutable.transliteration import Transliterator
        _translit = Transliterator()
    try:
        out = _translit.transliterate(itx, from_scheme="ITRANS", to_scheme="DEV")
    except Exception:
        return ""
    # A conversion that left Latin behind did not understand its input; better
    # no Devanagari title than a half-converted one.
    if not out or re.search(r"[A-Za-z]", out):
        return ""
    for pattern, repl in ITX_NASAL_FIXES:
        out = pattern.sub(repl, out)
    if ITX_HAS_NI_RE.search(itx):
        for pattern, repl in ITX_VOWEL_N_FIXES:
            out = pattern.sub(repl, out)
    return out


def clean(raw: str) -> str:
    """Strip tags and entities, collapse whitespace."""
    return " ".join(html.unescape(TAG_RE.sub(" ", raw)).split())


# The site is mid-cleanup on this: most credit lines now carry a bare name, but
# a few still trail the contributor's address, and one reaches `Author` -- which
# `build_tree.make_page` ships to every reader in tree.json. Publishing a
# personal address that upstream is itself removing is not ours to do, so the
# cut happens here, at the parse boundary, where it covers every credit field at
# once rather than one shipped field at a time.
#
# Both spellings the corpus uses are matched: `name@host.tld`, and the
# deliberately obfuscated `name at host.tld` that contributors write to dodge
# scrapers. The name is kept; only the address goes.
EMAIL_RE = re.compile(
    r"\s*<?\(?\b[\w.%+-]+(?:@|\s+at\s+)[\w-]+(?:\.[\w-]+)+\b\)?>?",
    re.IGNORECASE,
)


def strip_emails(value: str) -> str:
    """Drop email addresses from a free-text credit line, keeping the names.

    Applied to every `inf` field that names a person. Leaves a trailing comma
    behind when an address sat between two names, so the separators are
    re-collapsed afterwards.
    """
    if "@" not in value and " at " not in value:
        return value
    out = EMAIL_RE.sub("", value)
    out = re.sub(r"\s*,\s*(?=,)", "", out)
    return " ".join(out.split()).strip(" ,")


def parse_inf(page: str) -> dict[str, str]:
    match = INF_BLOCK_RE.search(page)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        hit = INF_LINE_RE.match(line.strip())
        if not hit:
            continue
        key, value = hit.group(1).strip(), hit.group(2).strip()
        # "NA" is the site's own placeholder for an unfilled field; drop it so
        # downstream code tests presence rather than a magic string.
        if value and value != "NA":
            fields[key] = value
    return fields


# The `inf` keys the corpus actually uses, folded to one entry per real field.
# Kept because the count is a published figure and the inventory cannot answer
# it: `parse_page` maps each key to a record field of its own name, so by the
# time a record exists the source's own vocabulary -- including the keys we
# extract nothing from -- is gone.
#
# Four of the 27 raw keys are the site spelling an existing field differently
# on a handful of documents, not fields of their own; `parse_page` folds each
# into its correct name, and they are folded here too so the count says how
# many things the site records rather than how many strings it has typed.
INF_KEY_VARIANTS = {
    "Description-comments": "Description/comments",
    "Encoded and proofread by": "Proofread by",
    "La Jagattest update": "Latest update",
    "Souce": "Source",
}


def source_fields(inf_keys: set[str]) -> int:
    """How many distinct fields the site fills in, variants folded."""
    return len({INF_KEY_VARIANTS.get(k, k) for k in inf_keys})


def parse_links(page: str) -> dict[str, str]:
    """Breadcrumb -> {label: href} for the .itx and PDF variants."""
    crumb = BREADCRUMB_RE.search(page)
    if not crumb:
        return {}
    links = {}
    for href, label in LINK_RE.findall(crumb.group(0)):
        text = clean(label)
        if text and text not in ("Home",) and not href.endswith("/"):
            links[text] = href
    return links


def parse_page(path: Path, location: str) -> dict:
    page = path.read_text(encoding="utf-8", errors="replace")
    inf = parse_inf(page)

    deva = SITENAME_RE.search(page)
    title_en = TITLE_RE.search(page)

    # `path.stem` is a FILESYSTEM fact; `doc_id` is the site's identity, and on
    # this corpus they differ for 34 pages. `fetch_text` appends a `~<hash>` to
    # ids that collide when case is folded (`gurvaShTakam`/`gurvashtakam` --
    # two different texts that a case-insensitive filesystem cannot hold side
    # by side), so the suffix belongs to the file, never to the document. Strip
    # it here and every downstream join -- topic pages, changelog, the tree --
    # sees the id the site itself uses. Keeping it in `doc_id` is what dropped
    # those 34 documents off the topics axis, and made their `source_url` point
    # at a page that does not exist upstream. `stem` keeps the suffix, because
    # `recount_sizes` opens the file by it.
    doc_id = f"{location}/{CASE_SUFFIX_RE.sub('', path.stem)}"
    # Devanagari from the banner where there is one; the ITRANS `itxtitle`
    # otherwise. Computed before the record so the "where did this come from"
    # flag can record what actually happened rather than what was attempted.
    title_deva = clean(deva.group(1)) if deva else ""
    deva_is_derived = False
    if not title_deva:
        title_deva = reconstruct_deva(inf.get("itxtitle", ""))
        deva_is_derived = bool(title_deva)
    # Raw spellings here; `collect` folds them to canonical ones once every
    # record is in hand, since choosing the surviving spelling needs corpus-wide
    # counts. See pipeline/categories.py, and notes/site-structure.md for why
    # folding by transliteration alone destroys real distinctions.
    categories = split_categories(inf.get("Category", ""))

    # `Sublocation` is the site's single canonical placement; `Category` is the
    # multi-valued facet a document is cross-listed under. They agree often but
    # not always, and only the first is a tree position.
    return {
        "doc_id": doc_id,
        "location": location,
        "stem": path.stem,
        "title": clean(title_en.group(1)) if title_en else doc_id.rpartition("/")[2],
        # The banner where the site provides one, else `itxtitle` rebuilt
        # (see reconstruct_deva -- an approximation, not a conversion). Never
        # the English `title`, which no converter can read -- a document with
        # neither keeps "" and the frontend shows its English label, unchanged,
        # in every scheme.
        "title_deva": title_deva,
        # True only where the banner was absent AND the rebuild succeeded. The
        # old name for this flag was `title_deva_from_itx`, which implied the
        # input was ITRANS and the output therefore exact; it is neither, and
        # the name misled a reader into treating the fallback as equivalent.
        "title_deva_reconstructed": deva_is_derived,
        "itxtitle": inf.get("itxtitle", ""),
        "sublocation": inf.get("Sublocation", ""),
        "categories": categories,
        "language": inf.get("Language", ""),
        "subject": strip_emails(inf.get("Subject", "")),
        "author": strip_emails(inf.get("Author", "")),
        "texttype": inf.get("Texttype", ""),
        "subdeity": inf.get("SubDeity", ""),
        "subcategory": inf.get("Subcategory", ""),
        # The input credit. `Encoded and proofread by` is the same slot under
        # another name -- the four documents carrying it carry no `Proofread
        # by`, so the site filled one slot, not two -- and it is the only place
        # in the corpus the site writes "encoded", which is what identifies
        # what this slot holds. See `audit.credit_stats`.
        "proofread_by": strip_emails(
            inf.get("Proofread by", "")
            or inf.get("Encoded and proofread by", "")
        ),
        "transliterated_by": strip_emails(inf.get("Transliterated by", "")),
        "translated_by": strip_emails(inf.get("Translated by", "")),
        # Upstream typo key, and a substitute rather than a duplicate: the one
        # document with `Souce` has no `Source`. Likewise `La Jagattest update`
        # below -- its document has no `Latest update`, so without the fold it
        # would drop out of the changelog entirely.
        "source": strip_emails(inf.get("Source", "") or inf.get("Souce", "")),
        "acknowledge_permission": strip_emails(
            inf.get("Acknowledge-Permission", "")
        ),
        "latest_update": inf.get("Latest update", "")
        or inf.get("La Jagattest update", ""),
        "description": strip_emails(
            inf.get("Description/comments", "")
            or inf.get("Description-comments", "")
        ),
        # Holds HTML -- `<a>` links to archive.org scans and related texts,
        # the same parentheticals `parse_scans` reads off the listing pages.
        # Kept raw, as `parse_inf` returns it; anything that renders it must
        # escape it, and nothing in the frontend gets it (see build_tree.
        # make_page, which enumerates `meta` explicitly).
        # Emails are cut here too: this field carries an `<!-- ... -->` comment
        # holding a contributor's address, which upstream clearly meant to keep
        # out of the rendered page. Nothing renders it, but nothing should
        # store it either.
        "indexextra": strip_emails(inf.get("Indexextra", "")),
        "source_url": f"https://sanskritdocuments.org/{doc_id}.html",
        "downloads": parse_links(page),
        "has_inf": bool(inf),
        # True on the 74 pages the site still renders with the older Sanscript
        # transliterator rather than Aksharamukha (see LEGACY_TRANSLIT_RE).
        "legacy_translit": bool(LEGACY_TRANSLIT_RE.search(page)),
        # The source's own key names, stripped by `collect` once it has counted
        # them. Never reaches the inventory -- it is a measurement of the page,
        # not a fact about the text, and 27 keys per record would cost ~2 MB.
        "_inf_keys": sorted(inf),
    }


def listing_slugs() -> set[str]:
    """The 87 `/sanskrit/<slug>/` listing names, from the cached listing pages.

    Reads LISTING_CACHE_DIR from config. It used to hardcode
    `data/listing_cache`, a directory that has never existed -- the pages live
    in `data/metadata_cache/listings` -- so this silently returned an empty set
    and every parse ran with categories unnormalized, warning as it went.
    """
    return {p.stem.removeprefix("sanskrit_")
            for p in LISTING_CACHE_DIR.glob("sanskrit_*.html")}


def canonical_spellings(records: list[dict], slugs: set[str]) -> dict[str, str]:
    """concept key -> the one spelling to display for it.

    The site spells the same concept several ways (`dhyAna`/`dhyAnam`), and the
    filter needs one option per concept, not one per spelling. Preference is the
    slug spelling where the concept names a real listing page -- that is the
    site's own name for it -- and otherwise the majority spelling, so the label
    matches what most documents actually carry. Ties break alphabetically to
    keep the choice stable across runs rather than dependent on file order.
    """
    key = build_category_key(slugs)
    # Two real slugs can key to one concept -- `/sanskrit/vishhnu/` and
    # `/sanskrit/vishnu/` are the same page under two names, and `ALIASES`
    # merges them on purpose. Whichever lands in this dict last wins, so the
    # order has to be decided rather than inherited from a set: iteration order
    # varies between processes, and it did, flipping 1,815 documents between
    # `vishnu` and `vishhnu` from one build to the next.
    #
    # `ALIAS_SURVIVORS` is the existing answer to exactly this question -- it is
    # what `parse_listings.dedupe_aliases` uses to pick which of two duplicate
    # topic pages to keep -- so the category label follows the topic page rather
    # than disagreeing with it. Sorted first so the fallback is stable too.
    by_slug = {}
    for slug in sorted(slugs, key=lambda s: (s in ALIAS_SURVIVORS, s)):
        by_slug[key(slug)] = slug

    counts: dict[str, Counter] = {}
    for record in records:
        for raw in record["categories"]:
            counts.setdefault(key(raw), Counter())[raw] += 1

    display = {}
    for concept, spellings in counts.items():
        if concept in by_slug:
            display[concept] = by_slug[concept]
        else:
            display[concept] = min(spellings.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return display


def normalize_categories(records: list[dict], slugs: set[str]) -> int:
    """Fold each document's raw tags to canonical spellings, in place.

    Returns how many DISTINCT raw spellings went in, which the caller stashes
    beside the inventory. The fold is lossy and many-to-one, so this number
    cannot be recovered from the folded records afterwards -- counting it here,
    while the raw strings are still in hand, is the only cheap place to get it.

    Done here rather than in the frontend on purpose: `docs/app.js` treats
    `meta.categories` as already-canonical and never folds or de-duplicates, so
    a variant added to `pipeline/categories.py` disappears from the UI on the
    next build with no frontend change. Order is preserved and duplicates
    dropped -- two raw spellings of one concept on the same document (13 such
    documents) would otherwise become two identical filter matches.
    """
    raw_spellings = {t for r in records for t in r["categories"]}
    if not slugs:
        return len(raw_spellings)
    key = build_category_key(slugs)
    display = canonical_spellings(records, slugs)
    for record in records:
        seen, folded = set(), []
        for raw in record["categories"]:
            canon = display[key(raw)]
            if canon in seen:
                continue
            seen.add(canon)
            folded.append(canon)
        record["categories"] = folded
    return len(raw_spellings)


def meta_path_for(inventory: Path) -> Path:
    """`…/site_inventory.jsonl` -> `…/site_inventory.meta.json`.

    Corpus-level figures that the folded inventory cannot answer. Keyed off the
    inventory path rather than a config constant so it follows whichever track
    wrote it, `--out` overrides included.
    """
    return inventory.with_suffix("").with_suffix(".meta.json")


def collect(docroot: Path) -> tuple[list[dict], dict]:
    """Parse every `<location>/<name>.html` under `docroot`.

    Returns the records and the corpus-level figures that no record can carry
    -- the raw category spellings before folding, and how many fields the
    source itself uses. Both are lost the moment the records exist, so they are
    counted here and written to the sidecar (see `meta_path_for`).

    Takes the docpage root directly rather than deriving it from a snapshot
    path, because the same layout holds for two different corpora: the
    Feb-2025 scrape's `docpage_html_dls/`, and our own `fulltext_cache/`
    from the 2026-08 fetch. The page format is identical between them (checked
    over a 200-page sample: `<pre class="inf">`, `#sitename` and the breadcrumb
    all present in every one), so one parser serves both.
    """
    if not docroot.is_dir():
        raise SystemExit(f"not a directory: {docroot}")

    records = []
    inf_keys: set[str] = set()
    for location_dir in sorted(p for p in docroot.iterdir() if p.is_dir()):
        for page in sorted(location_dir.glob("*.html")):
            record = parse_page(page, location_dir.name)
            inf_keys.update(record.pop("_inf_keys"))
            records.append(record)

    slugs = listing_slugs()
    if not slugs:
        print("  WARNING: no cached topic pages; categories left unnormalized.")
    raw_spellings = normalize_categories(records, slugs)
    return records, {"raw_category_spellings": raw_spellings,
                     "inf_keys": len(inf_keys),
                     "source_fields": source_fields(inf_keys)}


def report(records: list[dict]) -> None:
    total = len(records)
    print(f"documents:      {total}")
    print(f"folders:        {len({r['location'] for r in records})}")
    # Reported, not used: `sublocation` stopped shaping the tree on 2026-08-24
    # (see build_tree.build_by_location). Still parsed, so still counted here.
    print(f"sublocations:   {len({r['sublocation'] for r in records if r['sublocation']})}")
    # Records are already normalized by `collect`, so these are concepts, not
    # raw spellings -- one entry per thing the filter will offer as an option.
    cats = Counter(c for r in records for c in r["categories"])
    print(f"categories:     {len(cats)} concepts, "
          f"{sum(cats.values())} assignments")

    # How many of those concepts name a real listing page. Both figures move if
    # the site changes its vocabulary, so they are worth seeing on every parse.
    # Expect a shortfall of exactly 2, from two different causes -- both a
    # consequence of ALIASES merging spellings the site keeps as separate topic
    # pages (see pipeline/categories.py):
    #   1. `vishhnu` and `vishnu` are both slugs, but key to the same concept,
    #      so 87 slugs yield only 86 distinct keys.
    #   2. no concept keys to `gita`: the raw spellings are `gItA`/`giitaa`,
    #      which fold to `giitaa`, so that slug is left unmatched.
    EXPECTED_UNFOLDED_SHORTFALL = 2
    slugs = listing_slugs()
    if slugs:
        key = build_category_key(slugs)
        concepts = {key(c) for c in cats}
        browsable = concepts & {key(s) for s in slugs}
        print(f"  browsable:    {len(browsable)} name a topic page, "
              f"{len(concepts) - len(browsable)} name nothing")
        shortfall = len(slugs) - len(browsable)
        if shortfall != EXPECTED_UNFOLDED_SHORTFALL:
            print(f"  WARNING: {len(slugs)} topic pages but only "
                  f"{len(browsable)} matched (shortfall {shortfall}, expected "
                  f"{EXPECTED_UNFOLDED_SHORTFALL}) -- check the normalizer guard.")
    for field in ("has_inf", "title_deva", "author", "texttype", "proofread_by"):
        filled = sum(1 for r in records if r[field])
        print(f"  {field + ':':18}{filled}/{total}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    parser.add_argument("--docroot", type=Path,
                        help="parse this docpage root instead of the "
                             "snapshot's (e.g. data/fulltext_cache)")
    parser.add_argument("--out", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    docroot = args.docroot or (snapshot_root(args.snapshot) / DOCPAGE_DIRNAME)
    records, inventory_meta = collect(docroot)
    print(f"read:           {docroot}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    # A sidecar, not a header line in the .jsonl: every reader of that file
    # assumes one-record-per-line, and a corpus-level figure is not a record.
    # Derived from `--out` so it is two-track for free -- the snapshot writes
    # `snapshot_inventory.meta.json` beside its own inventory and neither track
    # can read the other's.
    meta_path = meta_path_for(args.out)
    meta_path.write_text(
        json.dumps(inventory_meta) + "\n", encoding="utf-8")

    if args.report:
        report(records)
    print(f"wrote:          {args.out}")
    print(f"wrote:          {meta_path}")


if __name__ == "__main__":
    main()
