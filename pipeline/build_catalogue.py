"""Rebuild `data/catalogue.jsonl` from the cached index, with no network.

The catalogue is the scrape list `fetch_text` walks: one record per document,
carrying its `doc_id`, its URL, and which topic pages name it. It is written by
`fetch_metadata` as a side effect of the tier-1 walk -- and *only* there, which
made it the one artifact in `data/` that could not be recovered from a cache
already on disk. This closes that gap.

**It is a pure function of `data/metadata_cache/listings/`**, the 87 pages that
walk already saved. Rebuilding costs no requests, needs no rivulet, and takes
about a second, so a lost or truncated catalogue is a local repair rather than
a ~108-request refetch of pages we are holding unchanged.

    make build-catalogue

The same seam `parse_index.py` was made public for. `parse_scans` and
`parse_listings` already read the cached index offline; the catalogue's parse
half simply stayed inside the fetch loop, and this lifts it out. The link
parsing is imported, never reimplemented -- if the two disagreed, the scrape
list would drift from what the fetchers believe the site holds.

**The nav is cut first**, via `strip_nav`. The site's dropdown menu is repeated
verbatim on all 87 listings and links documents directly, so parsing a whole
page files every one of those documents under every topic.

What this does NOT rebuild is the `locations/` corroboration pass, which
`fetch_metadata` runs as an independent witness to the same document set. That
pass writes no catalogue field; it exists to be compared, and comparing is
`audit`'s job.
"""

import argparse
import json

from pipeline.config import CATALOGUE_PATH, METADATA_CACHE_DIR
from pipeline.parse_index import (SITE_BASE, doc_id_of, docpage_links,
                                  strip_nav)


def build(cache_dir=METADATA_CACHE_DIR):
    """Every document the cached listings name, in listing order.

    Ordered by slug so the output is byte-stable across runs: the file is
    committed to nothing, but a stable order makes a diff against a freshly
    fetched catalogue mean something.
    """
    listings_dir = cache_dir / "listings"
    if not listings_dir.is_dir():
        raise SystemExit(
            f"no cached listings at {listings_dir}\n"
            f"  run `make fetch-metadata` once to populate the cache")

    documents = {}
    pages = sorted(listings_dir.glob("*.html"))
    for path in pages:
        slug = path.stem
        # Same cut as the fetcher, same reason -- see the module docstring.
        hrefs = docpage_links(strip_nav(path.read_text(encoding="utf-8")))
        for href in hrefs:
            doc_id = doc_id_of(href)
            documents.setdefault(doc_id, {
                "doc_id": doc_id,
                # Derived, never stored -- the same discipline `tree.json`
                # uses for document URLs.
                "url": f"{SITE_BASE}/{doc_id}.html",
                "listings": [],
            })["listings"].append(slug)
    return documents, len(pages)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache", type=lambda p: __import__("pathlib").Path(p),
                        default=METADATA_CACHE_DIR)
    parser.add_argument("--out", type=lambda p: __import__("pathlib").Path(p),
                        default=CATALOGUE_PATH)
    args = parser.parse_args()

    documents, pages = build(args.cache)

    # Write through a `.part` rename, the same guard `fetch_text` uses: a crash
    # here must not leave a truncated catalogue that reads as complete. That is
    # precisely the state this module exists to repair.
    part = args.out.with_suffix(args.out.suffix + ".part")
    with part.open("w", encoding="utf-8") as handle:
        for doc_id in sorted(documents):
            handle.write(json.dumps(documents[doc_id], ensure_ascii=False) + "\n")
    part.replace(args.out)

    print(f"read {pages} cached topic pages")
    print(f"wrote {len(documents):,} documents to {args.out}")


if __name__ == "__main__":
    main()
