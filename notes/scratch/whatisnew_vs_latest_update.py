"""Compare whatisnew "date added" against each document's `Latest update`.

Analysis only: reads two local files and prints a markdown report to stdout.
Writes nothing. Results are recorded in `whatisnew-vs-latest-update.md`, next
to this script.

Inputs, relative to the repo root (run from there):

    data/whatisnew_events.jsonl   one event per line: doc_id, verb
                                  (added|updated), date (YYYY-MM-DD), page.
                                  Built by `python -m pipeline.parse_whatisnew`.
    docs/data/tree.json           the November catalogue. Each document appears
                                  once in the folders branch, with its `Latest
                                  update` already parsed to `meta.updated`
                                  (YYYY-MM).

For every document in the folders branch, three month-precision values:

    added   earliest event with verb "added"
    first   earliest event of any verb (a moved or renamed document loses its
            "added" line and may keep only "updated")
    stamp   meta.updated

`added` and `first` are each compared with `stamp` and put in one bucket:

    no_event        no qualifying event (for `added`: no "added" event)
    same            same month as the stamp, so it adds nothing
    earlier         before the stamp: the expected direction, new information
    later_floor     after the stamp, but the event is in the log's opening
                    batch (2010-10) and the stamp predates the log's start
                    (2010-04). The log simply begins there, so this is a
                    floor, not a conflict.
    later_real      after the stamp otherwise: a genuine reversal
    no_stamp        the document has no parseable `Latest update`

Why the batch month is not the start month: the log's header says "since
April 2010", and its earliest entry is 2010-04-25, but April holds only 5
events. The bulk backfill is one day, 2010-10-03 (211 added + 210 updated).
Keyed to 2010-04, the floor bucket is empty. Both months are derived or checked
against the events file, so a changed input fails loudly rather than shifting
the bucket silently.

For `first`, real reversals are also split by the verb of that first event.
A later "updated" event means the stamp was not bumped, which is a different
failure from an "added" date that postdates the stamp.

Usage:

    python notes/scratch/whatisnew_vs_latest_update.py > /tmp/report.md
"""

import collections
import json
import random
import sys
from pathlib import Path

EVENTS = Path("data/whatisnew_events.jsonl")
TREE = Path("docs/data/tree.json")
LOG_START = "2010-04"
BATCH_MONTH = "2010-10"
CLOSE = 3  # months: a gap this small reads as preparing vs posting
SAMPLES = 10
BUCKETS = ("no_event", "same", "earlier", "later_floor", "later_real",
           "no_stamp")
# Gap bins for real reversals, in months (event minus stamp), inclusive.
GAP_BINS = ((1, 1), (2, 3), (4, 6), (7, 12), (13, 24), (25, 60), (61, None))


def month_index(ym):
    year, month = ym.split("-")[:2]
    return int(year) * 12 + int(month) - 1


def folder_documents(tree):
    """{doc_id: stamp-or-None} from the folders branch, where each document
    sits exactly once. The topics branch repeats documents, so it is skipped."""
    branches = tree["root"]["children"]
    folders = [b for b in branches if b["id"].startswith("loc")]
    if len(folders) != 1:
        sys.exit(f"expected one folders branch, found ids "
                 f"{[b['id'] for b in branches]}")
    docs = {}

    def walk(node):
        for page in node.get("pages", []):
            meta = page.get("meta") or {}
            docs[meta["doc_id"]] = meta.get("updated")
        for child in node.get("children", []):
            walk(child)

    walk(folders[0])
    return docs


def load_events():
    """({doc_id: [(month, verb), ...]}, Counter of events per day)."""
    events = collections.defaultdict(list)
    per_day = collections.Counter()
    with EVENTS.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                e = json.loads(line)
                events[e["doc_id"]].append((e["date"][:7], e["verb"]))
                per_day[e["date"]] += 1
    return events, per_day


def bucket(event, stamp):
    """Which bucket one (event month, stamp month) pair falls in, plus the gap
    in months for a reversal."""
    if stamp is None:
        return "no_stamp", None
    if event is None:
        return "no_event", None
    gap = month_index(event) - month_index(stamp)
    if gap == 0:
        return "same", None
    if gap < 0:
        return "earlier", None
    if event == BATCH_MONTH and stamp < LOG_START:
        return "later_floor", gap
    return "later_real", gap


def gap_histogram(gaps):
    rows = []
    for lo, hi in GAP_BINS:
        n = sum(1 for g in gaps if g >= lo and (hi is None or g <= hi))
        label = f"{lo}" if lo == hi else (f"{lo}+" if hi is None
                                          else f"{lo}-{hi}")
        rows.append((label, n))
    return rows


def main():
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    docs = folder_documents(tree)
    events, per_day = load_events()

    log_start = min(m for evs in events.values() for m, _ in evs)
    if log_start != LOG_START:
        sys.exit(f"log starts {log_start}, expected {LOG_START}; "
                 "re-check the floor rule before trusting the buckets")
    batch_day, batch_size = max(
        ((d, n) for d, n in per_day.items() if d.startswith("2010")),
        key=lambda dn: dn[1])
    if not batch_day.startswith(BATCH_MONTH):
        sys.exit(f"largest 2010 batch is {batch_day}, expected in "
                 f"{BATCH_MONTH}; re-check the floor rule")
    start_month_events = sum(n for d, n in per_day.items()
                             if d.startswith(LOG_START))

    results = {"added": collections.defaultdict(list),
               "first": collections.defaultdict(list)}
    gaps = {"added": [], "first": []}
    reversal_months = {"added": collections.Counter(),
                       "first": collections.Counter()}
    first_reversal_verb = collections.Counter()
    # The plain-terms view of `added`: same month, within CLOSE months, or
    # further, each split by direction (log earlier = past, later = future).
    by_distance = collections.Counter()
    floor_if_start_month = {"added": 0, "first": 0}
    updated_only = []

    for doc_id, stamp in docs.items():
        evs = events.get(doc_id, [])
        added = min((m for m, v in evs if v == "added"), default=None)
        first_ev = min(evs, default=None)
        first = first_ev[0] if first_ev else None
        if evs and added is None:
            updated_only.append(doc_id)
        if added and stamp:
            g = month_index(added) - month_index(stamp)
            side = "past" if g < 0 else "future"
            if g == 0:
                by_distance["same"] += 1
            elif abs(g) <= CLOSE:
                by_distance[f"close_{side}"] += 1
            else:
                by_distance[f"far_{side}"] += 1
                if side == "future" and added == BATCH_MONTH \
                        and stamp < LOG_START:
                    by_distance["far_future_floor"] += 1
        for name, value in (("added", added), ("first", first)):
            b, gap = bucket(value, stamp)
            results[name][b].append(doc_id)
            if (value == LOG_START and stamp and stamp < LOG_START):
                floor_if_start_month[name] += 1
            if b == "later_real":
                gaps[name].append(gap)
                reversal_months[name][value] += 1
                if name == "first":
                    # Earliest event in that month; "added" sorts first, so a
                    # same-month add+update counts as an add.
                    verbs = {v for m, v in evs if m == value}
                    first_reversal_verb[
                        "added" if "added" in verbs else "updated"] += 1

    orphan_events = sorted(set(events) - set(docs))
    rng = random.Random(0)

    out = []
    out.append(f"documents in the folders branch: {len(docs)}")
    out.append(f"  with a stamp: {sum(1 for s in docs.values() if s)}")
    out.append(f"documents with any whatisnew event: "
               f"{sum(1 for d in docs if d in events)}")
    out.append(f"event doc_ids not in the catalogue: {len(orphan_events)}")
    out.append(f"log start (earliest event month): {log_start}, "
               f"{start_month_events} events in that month")
    out.append(f"opening batch: {batch_day}, {batch_size} events in one day")
    out.append(f"floor bucket if keyed to {LOG_START} instead: "
               f"added {floor_if_start_month['added']}, "
               f"first {floor_if_start_month['first']}")
    out.append(f"updated events only, no added event: {len(updated_only)}")
    out.append("")
    both = sum(v for k, v in by_distance.items() if k != "far_future_floor")
    out.append(f"added vs stamp, plain terms ({both} documents with both):")
    out.append("")
    out.append("| | past (log earlier) | future (log later) | total |")
    out.append("|---|---:|---:|---:|")
    out.append(f"| same month | | | {by_distance['same']} |")
    for label, key in ((f"within {CLOSE} months", "close"),
                       (f"more than {CLOSE} months", "far")):
        p, f = by_distance[f"{key}_past"], by_distance[f"{key}_future"]
        out.append(f"| {label} | {p} | {f} | {p + f} |")
    out.append("")
    out.append(f"  of which future, more than {CLOSE} months, opening-batch "
               f"floor: {by_distance['far_future_floor']}")
    out.append("")
    out.append("| bucket | added | first |")
    out.append("|---|---:|---:|")
    for b in BUCKETS:
        out.append(f"| {b} | {len(results['added'][b])} "
                   f"| {len(results['first'][b])} |")
    out.append(f"| total | {sum(len(v) for v in results['added'].values())} "
               f"| {sum(len(v) for v in results['first'].values())} |")
    out.append("")
    out.append("first / later_real by verb of the first event: "
               + ", ".join(f"{v} {n}" for v, n in
                           sorted(first_reversal_verb.items())))
    out.append("")
    out.append("Real reversals: gap in months (event minus stamp)")
    out.append("")
    out.append("| gap | added | first |")
    out.append("|---|---:|---:|")
    for (label, a), (_, f) in zip(gap_histogram(gaps["added"]),
                                  gap_histogram(gaps["first"])):
        out.append(f"| {label} | {a} | {f} |")
    for name in ("added", "first"):
        g = sorted(gaps[name])
        if g:
            out.append("")
            out.append(f"{name}: median gap {g[len(g) // 2]}, max {g[-1]}; "
                       f"most common event months: "
                       + ", ".join(f"{m} ({n})" for m, n in
                                   reversal_months[name].most_common(5)))
    out.append("")
    out.append(f"Samples ({SAMPLES} per bucket, seeded, sorted)")
    for name in ("added", "first"):
        for b in BUCKETS:
            ids = sorted(results[name][b])
            if not ids:
                continue
            pick = sorted(rng.sample(ids, min(SAMPLES, len(ids))))
            out.append("")
            out.append(f"{name} / {b} ({len(ids)}):")
            for d in pick:
                evs = sorted(events.get(d, []))
                out.append(f"  {d}  stamp={docs[d]}  events="
                           + (",".join(f"{v[0]}:{m}" for m, v in evs) or "-"))
    ids = sorted(updated_only)
    out.append("")
    out.append(f"updated only ({len(ids)}):")
    for d in sorted(rng.sample(ids, min(SAMPLES, len(ids)))):
        out.append(f"  {d}  stamp={docs[d]}  events="
                   + ",".join(f"{v[0]}:{m}" for m, v in sorted(events[d])))
    print("\n".join(out))


if __name__ == "__main__":
    main()
