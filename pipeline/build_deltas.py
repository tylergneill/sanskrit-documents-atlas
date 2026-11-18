"""The site's change log -> docs/data/deltas.json, for the About page's Deltas.

**This reports what `https://sanskritdocuments.org/whatisnew` says, and only
that.** Every row on the page is one logged event: a document the site logged
as added or updated on a date. Nothing here is inferred from `Latest update`,
the dumps, or our own fetches, so the section can be read as the site's own
record, re-presented by period. What the log leaves out (removals, unlogged
edits, renamed documents' history) is the Data Quality section's business, not
this one's.

The corpus is used for one thing, labelling: a logged doc_id that resolves to a
document we hold (`parse_whatisnew.id_resolver`) gets that document's title and
a link. One that does not is still listed, by its stem, unlinked -- it is still
an event the site logged.

Output, kept flat so the page can regroup it by month, quarter or year:

    {"source": URL, "first": "YYYY-MM-DD", "last": "YYYY-MM-DD",
     "docs":   [[doc_id, title], ...],      title "" when not in the corpus
     "events": [[doc_index, "YYYY-MM-DD", verb], ...]   verb 1 added, 0 updated}

Run: python -m pipeline.build_deltas
"""

import argparse
import json
from pathlib import Path

from pipeline.config import (DELTAS_PATH, SITE_INVENTORY_PATH,
                             WHATISNEW_EVENTS_PATH)
from pipeline.parse_whatisnew import WHATISNEW_URL, id_resolver


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--events", type=Path, default=WHATISNEW_EVENTS_PATH)
    parser.add_argument("--inventory", type=Path, default=SITE_INVENTORY_PATH)
    parser.add_argument("--out", type=Path, default=DELTAS_PATH)
    args = parser.parse_args()

    if not args.events.exists():
        raise SystemExit(f"missing {args.events}; run `make fetch-whatisnew` "
                         "then `make parse-whatisnew` first.")
    if not args.inventory.exists():
        raise SystemExit(f"missing {args.inventory}; run `make parse-site` first.")

    titles = {}
    for line in args.inventory.open(encoding="utf-8"):
        record = json.loads(line)
        titles[record["doc_id"]] = record["title"] or record["stem"]
    resolve = id_resolver(set(titles))

    docs: list[list[str]] = []
    index: dict[str, int] = {}
    events = []
    seen = set()
    unresolved = 0
    for line in args.events.open(encoding="utf-8"):
        event = json.loads(line)
        doc_id = resolve(event["doc_id"])
        if doc_id is None:
            doc_id = event["doc_id"]
            unresolved += 1
        verb = 1 if event["verb"] == "added" else 0
        # A case-variant href and the canonical one can log the same event.
        key = (doc_id, event["date"], verb)
        if key in seen:
            continue
        seen.add(key)
        if doc_id not in index:
            index[doc_id] = len(docs)
            docs.append([doc_id, titles.get(doc_id, "")])
        events.append([index[doc_id], event["date"], verb])
    events.sort(key=lambda e: (e[1], e[0]))

    out = {
        "source": WHATISNEW_URL,
        "first": events[0][1] if events else None,
        "last": events[-1][1] if events else None,
        "docs": docs,
        "events": events,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, separators=(",", ":"))

    added = sum(1 for e in events if e[2])
    print(f"events:    {len(events)} ({added} added, {len(events) - added} updated)")
    print(f"documents: {len(docs)} ({sum(1 for d in docs if d[1])} in the corpus)")
    print(f"unmatched: {unresolved} events name a doc_id we do not hold")
    print(f"range:     {out['first']} -> {out['last']}")
    print(f"wrote:     {args.out} ({args.out.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()
