"""Stage 2b': the Feb-2025 scrape -> docs/data/snapshot_tree.json.

The Feb-2025 snapshot track, kept apart from the real one. It reads
`snapshot_inventory.jsonl` + `snapshot_sizes.jsonl` and writes its own file, so
that `build` cannot quietly publish 18-month-old data under today's date --
which is exactly what happened until 2026-08-18, when `build_tree` still read
the snapshot's inventory.

**Same shape as `build`, never combined with it.** Both emit the schema
`docs/app.js` consumes, and which file the frontend receives is a *serve-time*
choice (`make serve-snapshot`), never a build-time one. The two corpora differ:

    build            9756 documents, our 2026-08 fetch
    snapshot-tree    8547 documents, an earlier Feb-2025 scrape

The snapshot is smaller, older, and not ours. It survives only as a
cross-check -- being able to diff what changed in 18 months -- and goes away
with the rest of the snapshot track once that comparison is done
(`notes/scratch/todo.md`).

Everything here is `build_tree`'s logic with different defaults; no builder
code is duplicated, so a fix to one is a fix to both.

Run: python -m pipeline.build_snapshot_tree
"""

import sys

from pipeline import build_tree
from pipeline.build_snapshot_changelog import SNAPSHOT_TAKEN
from pipeline.config import (INVENTORY_PATH, LISTINGS_PATH, SIZES_PATH,
                             SNAPSHOT_TREE_PATH)


def main() -> None:
    # Defaults only: an explicit flag on the command line still wins, because
    # argparse sees these first and the user's copy comes later.
    forced = ["--inventory", str(INVENTORY_PATH),
              "--sizes", str(SIZES_PATH),
              "--listings", str(LISTINGS_PATH),
              # The snapshot's own capture date, not the fetch journal's:
              # build_tree defaults its date ceiling to when OUR corpus was
              # taken, which on this track would let a 2026 stamp through
              # into a tree that ends in Feb 2025. Same constant and same
              # reason as build_snapshot_changelog.
              "--corpus-date", SNAPSHOT_TAKEN,
              "--out", str(SNAPSHOT_TREE_PATH)]
    sys.argv = [sys.argv[0]] + forced + sys.argv[1:]
    print("track:        SNAPSHOT (earlier Feb-2025 scrape, not the live corpus)")
    build_tree.main()


if __name__ == "__main__":
    main()
