"""Stage 2a: snapshot docpage bodies -> data/snapshot_sizes.jsonl.

Measures each document three ways -- raw page bytes, extracted body bytes, and
the byte length of that body transliterated DEV->IAST. All three are pure
functions of the cached page, and the snapshot is static, so this runs once and
`build_tree` just reads the result.

The body is the `<div id="Body">` / `<PRE>` region: the text itself, without the
site chrome, the `% Field : value` block, or the boilerplate reuse notice. Those
surround every page and would otherwise swamp the short stotras, which are most
of the corpus.

The DEV->IAST pass is the slow part; the point of caching is that a normal build
pays none of it. `build_tree` trusts the cache as-is; whatever updates the
snapshot is what reruns this.

Run: python -m pipeline.recount_sizes [--workers N]
"""

import argparse
import html
import json
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pipeline.config import DOCPAGE_DIRNAME, INVENTORY_PATH, SIZES_PATH, snapshot_root

STAT_KEYS = ("raw_bytes", "content_bytes", "transliterated_bytes")

# The text sits in <pre> inside `<div id="article">`. That id is the one the
# original scrape's notebook keyed on, and it holds on 799 of 800 sampled pages;
# `id="Body"` (the sibling atlas's container) appears on none of them, so
# guessing by analogy silently measured the whole page instead.
BODY_RE = re.compile(
    r'<div id="article".*?>(.*?)</div>', re.DOTALL | re.IGNORECASE
)
PRE_RE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL | re.IGNORECASE)
# The metadata table is itself a <pre class="inf"> -- excluded by the BodyHref
# cut above, but guarded here too in case a page nests it differently.
INF_PRE_RE = re.compile(r'<pre class="inf">.*?</pre>', re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")

_transliterator = None


def _get_transliterator():
    """skrutable is slow to import, so each pool worker builds one lazily."""
    global _transliterator
    if _transliterator is None:
        from skrutable.transliteration import Transliterator
        _transliterator = Transliterator(from_scheme="DEV", to_scheme="IAST")
    return _transliterator


def extract_body(page: str) -> str:
    """The document text, stripped of chrome, tags, and entities."""
    match = BODY_RE.search(page)
    region = match.group(1) if match else page
    region = INF_PRE_RE.sub("", region)

    blocks = PRE_RE.findall(region)
    # No <pre> means an unusual layout; fall back to the whole region rather
    # than reporting the document as empty.
    text = "\n".join(blocks) if blocks else region

    return html.unescape(TAG_RE.sub("", text)).strip()


def measure(args: tuple[str, str]) -> tuple[str, dict]:
    """Worker: read one docpage and return its three byte figures."""
    doc_id, path = args
    page = Path(path).read_text(encoding="utf-8", errors="replace")
    content = extract_body(page)

    stats = {
        "raw_bytes": len(page.encode("utf-8")),
        "content_bytes": len(content.encode("utf-8")),
        "transliterated_bytes": 0,
    }
    if content:
        iast = _get_transliterator().transliterate(content)
        stats["transliterated_bytes"] = len(iast.encode("utf-8"))
    return doc_id, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    parser.add_argument("--docroot", type=Path,
                        help="measure this docpage root instead of the "
                             "snapshot's (e.g. data/fulltext_cache)")
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--out", type=Path, default=SIZES_PATH)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    if not args.inventory.exists():
        raise SystemExit(f"missing {args.inventory}; run `make parse` first.")

    # Same two-corpus split as parse_snapshot: the snapshot's docpage root, or
    # our own fulltext_cache. Pass the docroot that matches the inventory --
    # measuring one corpus against the other's inventory silently drops every
    # document the two do not share.
    docroot = args.docroot or (snapshot_root(args.snapshot) / DOCPAGE_DIRNAME)

    jobs = []
    for line in args.inventory.open(encoding="utf-8"):
        record = json.loads(line)
        path = docroot / record["location"] / f"{record['stem']}.html"
        if path.exists():
            jobs.append((record["doc_id"], str(path)))

    try:
        from tqdm import tqdm
    except ImportError:
        def tqdm(it, **kw):
            return it

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool, \
            args.out.open("w", encoding="utf-8") as handle:
        for doc_id, stats in tqdm(
            pool.map(measure, jobs, chunksize=32),
            total=len(jobs),
            desc="measuring",
        ):
            handle.write(
                json.dumps({"doc_id": doc_id, **stats}, ensure_ascii=False) + "\n"
            )
            written += 1

    print(f"measured: {written}/{len(jobs)}")
    print(f"wrote:    {args.out}")


if __name__ == "__main__":
    main()
