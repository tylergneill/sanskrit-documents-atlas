"""Stage 3': the Feb-2025 scrape -> docs/data/snapshot_changelog.json.

The Feb-2025 snapshot's growth curve, kept apart from the real one exactly as
`build_snapshot_tree` keeps its tree apart. It reads `snapshot_inventory.jsonl`
+ `snapshot_sizes.jsonl` and writes its own file, so that `changelog` cannot
quietly publish an 18-month-old curve -- which is what happened until
2026-08-19, when `build_changelog` still read the snapshot's inventory.

**Same shape as `changelog`, never combined with it.** Both emit the record
list `docs/about.js` consumes. The two corpora differ:

    changelog           9756 documents, our 2026-08 fetch
    snapshot-changelog  8547 documents, an earlier Feb-2025 scrape

Two defaults are forced beyond the paths, and both matter:

  * `--corpus-date 2025-02-16`, the day the snapshot was taken. It caps every
    `Latest update` above it as an upstream typo. The real track derives its
    own ceiling from the fetch journal instead, which is why this cannot stay
    a module-level constant.

  * `--catalogue`, folding the documents the live site lists but the snapshot
    never held into a final counts-only bucket. That is the honest way to show
    a stale corpus against a moved site -- 1254 documents, `sizes_partial`,
    because they are counted and not measured. On the real track there is
    nothing to fold: the corpus IS the catalogue.

Everything here is `build_changelog`'s logic with different defaults; no
builder code is duplicated, so a fix to one is a fix to both.

Run: python -m pipeline.build_snapshot_changelog
"""

import sys

from pipeline import build_changelog
from pipeline.config import (CATALOGUE_PATH, INVENTORY_PATH,
                             SNAPSHOT_CHANGELOG_PATH, SIZES_PATH)

# The day the Feb-2025 scrape was taken. Fixed, because the snapshot is.
SNAPSHOT_TAKEN = "2025-02-16"


def main() -> None:
    # Defaults only: an explicit flag on the command line still wins, because
    # argparse sees these first and the user's copy comes later.
    forced = ["--inventory", str(INVENTORY_PATH),
              "--sizes", str(SIZES_PATH),
              "--catalogue", str(CATALOGUE_PATH),
              "--corpus-date", SNAPSHOT_TAKEN,
              "--out", str(SNAPSHOT_CHANGELOG_PATH)]
    sys.argv = [sys.argv[0]] + forced + sys.argv[1:]
    print("track:     SNAPSHOT (earlier Feb-2025 scrape, not the live corpus)")
    build_changelog.main()


if __name__ == "__main__":
    main()
