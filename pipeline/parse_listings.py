"""Stage 1c: the snapshot's listing pages -> data/snapshot_listings.jsonl.

The site files each text in exactly one `Location`, but *browsing* happens
through 87 listing pages at `/sanskrit/<slug>/`, and those overlap freely: a
text sits on one to ten of them. That makes listings a third axis, distinct
from both the canonical location and the free-text `Category` facet -- and the
honest one, since the 87 pages are the site's own curated navigation rather
than an uncontrolled metadata field.

This reads the 87 pages already in the snapshot (`subpage_html_dls/`), so it
costs no requests. `fetch_metadata.py` fetches the same pages live; the two
share their parsing helpers, and this stage is the offline half.

One record per listing page:

    {"slug": "ashtaka", "title": "aShTaka", "doc_ids": [...], "count": 964}

Run: python -m pipeline.parse_listings
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from pipeline.config import LISTINGS_PATH, SUBPAGE_DIRNAME, snapshot_root
from pipeline.parse_index import docpage_links, doc_id_of, strip_nav

# The listing pages carry no <title>; the visible name is this heading. Read
# only to detect the site serving one page at two URLs -- NOT used as the node's
# title, see parse_listing.
HEADING_RE = re.compile(
    r'<h1[^>]*class="[^"]*index-header[^"]*"[^>]*>([^<]+)', re.IGNORECASE)

# The nav cut itself lives in fetch_metadata beside the other link parsing,
# so the offline and networked halves read a listing page identically.


def parse_listing(path: Path) -> dict:
    """One cached listing page -> its slug, display title, and membership."""
    page = path.read_text(encoding="utf-8", errors="replace")

    # Snapshot files are named `sanskrit_<slug>.html`, mirroring the site's
    # `/sanskrit/<slug>/`. The bare slug is what the Category field would use.
    slug = path.stem.removeprefix("sanskrit_")

    # **The slug is the title.** These nodes name the site's own
    # `/sanskrit/<slug>/` pages, and the sidebar has to reproduce them exactly:
    # a reader matching a `Category` tag against the tree needs the string the
    # site uses, not a heading that may disagree with it.
    #
    # It does disagree. `/sanskrit/vishnu/` serves the `vishhnu` page byte for
    # byte, so trusting the heading rendered TWO sidebar rows both labelled
    # `vishhnu`. The slugs were always distinct; only the displayed name
    # collapsed them. (That duplicate is now dropped outright -- see `collect`.)
    heading = HEADING_RE.search(page)
    title = slug
    heading_text = heading.group(1).strip() if heading else ""

    body = strip_nav(page)

    # dict.fromkeys, not set(): a document linked twice from one listing (the
    # heading entry plus its download row) is one membership, but the site's own
    # ordering is worth preserving.
    doc_ids = list(dict.fromkeys(doc_id_of(h) for h in docpage_links(body)))

    return {
        "slug": slug,
        "title": title,
        # What the page called itself, kept so `--report` can flag a mismatch.
        # Not displayed anywhere.
        "heading": heading_text,
        "url": f"https://sanskritdocuments.org/sanskrit/{slug}/",
        "doc_ids": doc_ids,
        "count": len(doc_ids),
    }


# **A human annotation, deliberately.** Detection below is automatic; WHICH of
# a duplicated pair survives is a judgement call this list records, because
# "the less mangled spelling" is not something the data can decide.
#
#   vishnu   over vishhnu   -- `shh` for retroflex s is the site's own
#                              invention; ITRANS would be `viShNu`
#   gita     over giitaa    -- and `gita` is also the larger page (138 vs 135)
#
# Verified 2026-08-23 to be the complete set: across all 3741 pairs of the 87
# pages, only these two exceed 50% containment (100% and 97.8%). The next
# closest relationship is deities_misc/gurudev at 58% Jaccard, which is overlap
# between two real pages, not duplication. If the site adds another duplicate,
# `dedupe_aliases` will suppress it keeping whichever slug sorts first --
# stable, but arbitrary. Add it here to choose on purpose.
ALIAS_SURVIVORS = {"vishnu", "gita"}

# How much of the larger page a smaller one must cover before it is treated as
# a redundant near-copy rather than a narrower page in its own right.
#
# This threshold is doing real work, and it is why subset alone is NOT the
# rule. Nine slugs sit strictly inside another: `durga` (143) inside `devii`
# (2144), `vishnu_misc` (29) inside `vishnu` (1822), `venkateshwara` inside
# `vishnu`, and so on. Those are exactly what the listing axis is for -- a
# narrow page nested in a broad one -- and dropping them would delete the axis.
# They cover 1-7% of their superset. `giitaa` covers 98% of `gita`, in the same
# order, which is a different thing entirely: one page with three entries
# added. Nothing observed sits between 7% and 98%.
NEAR_DUPLICATE_COVERAGE = 0.95


def dedupe_aliases(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Drop listing pages the site serves twice, keeping one of each.

    `/sanskrit/vishnu/` returns the `/sanskrit/vishhnu/` page byte for byte --
    two URLs, two 200s, one page. Rendering both put a useless duplicate row in
    the tree: same 1822 documents, same size, nothing to tell them apart, and
    1822 memberships of double-counting in the axis total.

Two cases, both keyed on MEMBERSHIP rather than on name, so a future
    alias is caught without anyone having to notice it first:

    1. **Identical** -- `/sanskrit/vishnu/` and `/sanskrit/vishhnu/`, the same
       bytes served at two URLs.
    2. **Near-identical** -- `/sanskrit/giitaa/` holds 135 documents, every one
       of them among `/sanskrit/gita/`'s 138 and in the same order. Two real
       pages (different headings, different file sizes), but the smaller says
       nothing the larger does not.

    Case 2 needs `NEAR_DUPLICATE_COVERAGE`; see the note there for why a bare
    subset test would delete half the axis.

    Returns `(kept, dropped)` -- dropped is not waste, it is what the audit
    publishes as a finding about the source.
    """
    by_members = {}
    for record in records:
        key = tuple(record["doc_ids"])
        if not key:
            continue
        by_members.setdefault(key, []).append(record)

    kept, dropped = [], []
    duplicated = {id(r) for group in by_members.values() if len(group) > 1
                  for r in group}
    for group in by_members.values():
        if len(group) < 2:
            continue
        slugs = sorted(r["slug"] for r in group)
        winner = next((s for s in slugs if s in ALIAS_SURVIVORS), slugs[0])
        for record in group:
            if record["slug"] == winner:
                # Name the URLs this row also stands for, so the tree can say so.
                record["aliases"] = [s for s in slugs if s != winner]
                record["alias_notes"] = {
                    s: "byte-identical copy of" for s in record["aliases"]}
            else:
                dropped.append(record)

    # Case 2: a page whose entire membership sits inside another, covering
    # nearly all of it. Compared against what survived case 1, and largest
    # first, so a chain settles on one winner.
    dropped_ids = {id(r) for r in dropped}
    survivors = [r for r in records if id(r) not in dropped_ids]
    by_size = sorted(survivors, key=lambda r: -len(r["doc_ids"]))
    for i, bigger in enumerate(by_size):
        big = set(bigger["doc_ids"])
        if not big or id(bigger) in dropped_ids:
            continue
        for smaller in by_size[i + 1:]:
            if id(smaller) in dropped_ids or not smaller["doc_ids"]:
                continue
            small = set(smaller["doc_ids"])
            if small < big and len(small) / len(big) >= NEAR_DUPLICATE_COVERAGE:
                # Respect an explicit survivor choice even against size.
                if smaller["slug"] in ALIAS_SURVIVORS and bigger["slug"] not in ALIAS_SURVIVORS:
                    continue
                smaller["subset_of"] = bigger["slug"]
                smaller["missing_from_subset"] = len(big - small)
                dropped.append(smaller)
                dropped_ids.add(id(smaller))
                bigger.setdefault("aliases", []).append(smaller["slug"])
                bigger.setdefault("alias_notes", {})[smaller["slug"]] = (
                    f"strict subset ({len(small)} of {len(big)}) of")

    kept = [r for r in records if id(r) not in dropped_ids]
    return kept, dropped


def collect(subroot: Path) -> list[dict]:
    """Parse every cached `sanskrit_<slug>.html` under `subroot`.

    Takes the directory directly, because the same 87 pages exist twice: in the
    snapshot's `subpage_html_dls/`, and in `data/metadata_cache/listings/` from
    our own tier-1 fetch. Filenames and markup match, so one parser serves both.

    Aliased pages are dropped here rather than downstream, so every consumer --
    the tree, the report, the audit -- sees the same 86.
    """
    if not subroot.is_dir():
        raise SystemExit(f"not a directory: {subroot}")
    records = [parse_listing(p) for p in sorted(subroot.glob("sanskrit_*.html"))]
    kept, _ = dedupe_aliases(records)
    return kept


def report(records: list[dict], inventory_path: Path) -> None:
    total = sum(r["count"] for r in records)
    print(f"topic pages:    {len(records)}")
    print(f"memberships:    {total}")

    per_doc = Counter()
    for record in records:
        for doc_id in record["doc_ids"]:
            per_doc[doc_id] += 1
    print(f"documents:      {len(per_doc)} distinct, "
          f"{total / len(per_doc):.2f} pages each on average")

    spread = Counter(per_doc.values())
    buckets = ", ".join(f"{n}:{spread[n]}" for n in sorted(spread))
    print(f"pages per doc:  {buckets}")

    # Pages the site serves at more than one URL, already dropped by `collect`.
    # Printed rather than swallowed: it is the site's own doing, not a parse
    # artifact, and the audit publishes it as a finding.
    for record in records:
        for alias in record.get("aliases") or []:
            note = record.get("alias_notes", {}).get(alias, "duplicate of")
            print(f"suppressed:     /{alias}/ is a {note} /{record['slug']}/; "
                  f"kept /{record['slug']}/")

    # The listings enumerate the live site; the inventory is what we hold. The
    # gap in either direction is the interesting part, so report both rather
    # than silently intersecting.
    if inventory_path.exists():
        held = {json.loads(line)["doc_id"]
                for line in inventory_path.open(encoding="utf-8")}
        listed = set(per_doc)
        print(f"held, unlisted: {len(held - listed)}")
        print(f"listed, unheld: {len(listed - held)}")
    else:
        print(f"(no {inventory_path.name}; run `make parse` to compare)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    parser.add_argument("--listing-dir", type=Path,
                        help="parse this listing directory instead of the "
                             "snapshot's (e.g. data/metadata_cache/listings)")
    parser.add_argument("--out", type=Path, default=LISTINGS_PATH)
    parser.add_argument("--inventory", type=Path, default=None)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    subroot = args.listing_dir or (snapshot_root(args.snapshot) / SUBPAGE_DIRNAME)
    records = collect(subroot)
    print(f"read:           {subroot}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    if args.report:
        from pipeline.config import INVENTORY_PATH
        report(records, args.inventory or INVENTORY_PATH)
    print(f"wrote:          {args.out}")


if __name__ == "__main__":
    main()
