"""Dating input: the 2020 site mirror -> data/dump2020_inventory.jsonl.

A third observation of the corpus, four and a half years older than the Feb-2025
snapshot and six older than our own fetch. It is **not a build track** -- no
tree and no changelog is built from it, and it must never be served. It exists
to date the other two.

Why it is worth having: `Latest update` is the most recent touch, so for any
revised document it sits *later* than the document's arrival, and the error runs
one way only. Nothing ever buckets earlier than it arrived, so the growth curve
is a lower bound whose early years are systematically thin. Presence in a dated
mirror is the independent fact that fixes this -- a document the 2020 mirror
holds existed by then no matter what its stamp says now. See
`build_changelog --attest`, which consumes this file.

The mirror is a `wget -r` of the whole site, so most of its ~10900 HTML files
are not document pages: `sites/`, `mirrors/`, `learning_tools/`, the per-script
directories (`iast/`, `itrans/`, `tamil/`, ...) and the root navigation. The
document pages are the ~4700 under `doc_<location>/`, and the page format is
byte-identical in shape to both later corpora -- same `<div id="article">`, same
`<pre class="inf">` -- so `parse_snapshot` reads them unchanged. This module
only builds the directory view that parser expects.

Run: python -m pipeline.parse_dump_2020 [--dump PATH] [--report]
"""

import argparse
import json
import tempfile
from pathlib import Path

from pipeline.config import (DUMP_2020_DATE, DUMP_2020_INVENTORY_PATH,
                             dump_2020_root)
from pipeline.parse_snapshot import collect


def build_docroot(mirror: Path, into: Path) -> int:
    """Symlink `doc_<location>/` into a flat docroot, prefix intact.

    `parse_snapshot` walks `<docroot>/<location>/<stem>.html` and derives
    `doc_id` as `<location>/<stem>`. Both other corpora keep the `doc_` prefix
    in `location`, so it is kept here too -- stripping it yields ids like
    `devii/x` against their `doc_devii/x` and every join silently returns
    nothing.
    """
    into.mkdir(parents=True, exist_ok=True)
    linked = 0
    for directory in sorted(mirror.glob("doc_*")):
        if not directory.is_dir():
            continue
        link = into / directory.name
        if not link.exists():
            link.symlink_to(directory)
        linked += 1
    return linked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", default=None,
                        help="the mirror root (the `sanskritdocuments.org` "
                             "directory); defaults to SDA_DUMP_2020 or the "
                             "checkout beside this repo")
    parser.add_argument("--out", type=Path, default=DUMP_2020_INVENTORY_PATH)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    mirror = dump_2020_root(args.dump)
    if not mirror.is_dir():
        raise SystemExit(
            f"missing 2020 mirror: {mirror}\n"
            "Clone it, or point SDA_DUMP_2020 at your copy.")

    # The view is derivative and cheap; rebuilding it each run keeps it from
    # going stale against a moved or re-cloned mirror.
    with tempfile.TemporaryDirectory(prefix="sda-dump2020-") as tmp:
        docroot = Path(tmp) / "docroot"
        locations = build_docroot(mirror, docroot)
        if not locations:
            raise SystemExit(
                f"no doc_* directories under {mirror}; is this the mirror "
                "root rather than the repo root?")
        records, _ = collect(docroot)

    print(f"read:       {mirror}")
    print(f"observed:   {DUMP_2020_DATE}")
    print(f"folders:    {locations}")
    print(f"documents:  {len(records)}")

    if args.report:
        dated = sum(1 for r in records if r.get("latest_update"))
        print(f"  dated:    {dated}/{len(records)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote:      {args.out}")


if __name__ == "__main__":
    main()
