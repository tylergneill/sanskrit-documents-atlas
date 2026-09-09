"""Stage 3: per-document update dates -> docs/data/changelog.json.

Every document carries its own `Latest update` in the metadata block, spanning
1992 to the present. That is a thirty-year history already sitting in the
corpus, so the changelog is derived from the documents themselves rather than
from repeated observations of them.

What a bucket means: **the documents whose most recent update falls in that
period**, with their sizes. It is not a full revision history -- the site
records only the latest touch per document, so a text updated in 2015 and again
in 2023 appears once, in 2023, and its earlier state is not recoverable. The
cumulative totals are therefore "documents last touched on or before date X",
which tracks the collection's growth but understates churn.

Emits the record shape the sanskrit-wikisource-atlas frontend consumes, so
`docs/about.js` renders it unchanged.

**Two tracks, never combined**, exactly as `build` and `snapshot-tree` are.
This module defaults to OUR fetch; `build_snapshot_changelog` is the thin
wrapper that points it at the earlier Feb-2025 scrape and writes its own
file.

    changelog           site_inventory + site_sizes  -> changelog.json           9756 docs
    snapshot-changelog  snapshot_* equivalents       -> snapshot_changelog.json  8547 docs

Until 2026-08-19 there was only one track and it read the snapshot, so the
published curve was 8547 documents ending in Feb 2025 -- with the 1254
documents our own fetch already held bolted on as a synthetic final bucket
carrying no sizes and the catalogue's file mtime for a date. The same drift
`build` had, caught later because a growth curve looks plausible while wrong.

`--catalogue` still folds in documents the live catalogue lists that the corpus
being read does not hold, flagged `sizes_partial` since they are counted rather
than measured. That is meaningful for the snapshot, which is 1254 documents
behind the site. It is off by default on the real track, where the corpus IS
the catalogue and the residue is only the 25 documents the site 404s.

**Monthly is the published granularity**, and it is a cross-atlas contract
rather than a local preference: sagara-sangama plots all three collections on
one time axis, and a yearly series there is a straight line between Decembers
laid over its neighbours' real shape. `--granularity year` still works for a
quick local look, but what ships in docs/data/ is months.

Run: python -m pipeline.build_changelog [--granularity month|year]
"""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import (CATALOGUE_PATH, CHANGELOG_PATH,
                            SITE_INVENTORY_PATH, SITE_SIZES_PATH,
                            TEXT_LOG_PATH)

STAT_KEYS = ("raw_bytes", "content_bytes", "transliterated_bytes")

# `Latest update` is free text and varies more than it looks: abbreviated
# months ("Dec. 27, 1997"), a misspelling ("Julu 11, 2018"), ranges
# ("September 18-19, 2023 Ganeshachaturthi"), a period for the comma
# ("February 25. 2023"), and a missing day ("April, 2021"). The day is only
# used to order within a bucket, so it defaults to the 1st when absent.
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}
# Prefix match covers both "Dec" and "December"; "Julu" is a typo for July.
MONTH_ALIASES = {
    **{m[:3]: i for m, i in MONTHS.items()},
    "sept": 9,
    # Upstream typos, each appearing once or twice. Listed explicitly rather
    # than fuzzy-matched so a genuinely unknown string still fails loudly.
    "julu": 7, "jnuary": 1, "narch": 3, "aoril": 4, "septyember": 9,
    "ocober": 10, "noember": 11, "deember": 12,
}

# `\s*` after the comma, not `\s+`: "January 5,2005" and "October 8,2022" omit
# the space. A trailing `\s*` before the year covers the same for the day.
DATE_RE = re.compile(
    r"([A-Za-z]{3,10})\.?,?\s+(?:(\d{1,2})(?:\s*-\s*\d{1,2})?,?\.?\s*)?"
    r"((?:19|20)\d\d)"
)
# "11-Feb-2015" -- one entry, the only ISO-ish form in the corpus.
DMY_RE = re.compile(r"(\d{1,2})-([A-Za-z]{3,9})-((?:19|20)\d\d)")
# A bare year with no month ("1996"), the last resort before giving up.
YEAR_ONLY_RE = re.compile(r"\b((?:19|20)\d\d)\b")


def month_number(name: str) -> int | None:
    key = name.lower()
    return MONTHS.get(key) or MONTH_ALIASES.get(key) or MONTH_ALIASES.get(key[:3])

# A document cannot have been updated after the corpus holding it was
# captured, so that capture date is the ceiling: anything later is an upstream
# typo (two exist, dated 2027 and 2029). Clamping rather than dropping keeps
# the document in its collection's counts while refusing to invent a future
# bucket.
#
# **Per-track, so it is a required argument and not a constant.** It was the
# module-level `SNAPSHOT_TAKEN = 2025-02-16` until 2026-08-19, which on our own
# corpus silently rewrites every genuinely-2026 document back into February
# 2025 -- 386 of them. The snapshot's date now lives in
# `build_snapshot_changelog`, the only place that should know it; leaving a
# copy here as a default would just reinstate the same trap for the next
# caller.


def corpus_date(log_path: Path) -> datetime:
    """The newest `fetched_at` in the fetch journal -- when our corpus was taken.

    Same source `build_tree` stamps `__content_version__` from, so the ceiling
    here and the date in the topbar cannot drift apart. Falls back to now when
    the journal is absent, which only happens on a corpus nothing fetched.
    """
    newest = ""
    if log_path.exists():
        for line in log_path.open(encoding="utf-8"):
            stamp = json.loads(line).get("fetched_at") or ""
            if stamp > newest:
                newest = stamp
    if not newest:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(newest).astimezone(timezone.utc)


def parse_update(raw: str, ceiling: datetime) -> datetime | None:
    """`Latest update` -> a date, or None if it lacks a year.

    A handful of entries read like "September 2" with no year at all; they are
    unplaceable and excluded rather than guessed at.
    """
    if not raw:
        return None
    dmy = DMY_RE.search(raw)
    if dmy:
        day, month_name, year = dmy.groups()
    else:
        match = DATE_RE.search(raw)
        if match:
            month_name, day, year = match.groups()
        else:
            # No month at all. One entry reads just "1996"; place it at the
            # start of that year rather than losing the document.
            bare = YEAR_ONLY_RE.search(raw)
            if not bare:
                return None
            month_name, day, year = "january", "1", bare.group(1)

    month = month_number(month_name)
    if month is None:
        return None
    try:
        parsed = datetime(int(year), month, int(day) if day else 1,
                          tzinfo=timezone.utc)
    except ValueError:
        # An impossible day ("August 43, 2018"). The month and year are still
        # good, which is all a yearly or monthly bucket needs.
        parsed = datetime(int(year), month, 1, tzinfo=timezone.utc)
    return min(parsed, ceiling)


def load_attestations(paths: list[Path]) -> dict[str, datetime]:
    """`doc_id` -> the earliest date any older dump was observed to hold it.

    An **arrival ceiling that no later revision can lift.** `Latest update` is
    the most recent touch, so for a revised document it sits later than the
    document's arrival and the error runs one way only: a text encoded in 2004
    and reproofed in 2021 buckets as 2021, and nothing ever buckets earlier
    than it arrived. Presence in a dated dump is the independent fact that
    resists that -- it proves the document existed by the dump's date whatever
    its stamp now claims.

    Each path is a `parse_snapshot` inventory plus the date that corpus was
    captured, as `PATH:YYYY-MM-DD`. The dump's own `latest_update` is read too
    and the *earlier* of the two wins: a document the 2020 dump already stamped
    2004 attests 2004, not 2020.
    """
    attested: dict[str, datetime] = {}
    for spec in paths:
        raw = str(spec)
        path_part, _, date_part = raw.rpartition(":")
        if not path_part or not date_part:
            raise SystemExit(f"--attest needs PATH:YYYY-MM-DD, got {raw!r}")
        observed = datetime.fromisoformat(date_part).replace(tzinfo=timezone.utc)
        source = Path(path_part)
        if not source.exists():
            raise SystemExit(f"missing attestation inventory: {source}")
        for line in source.open(encoding="utf-8"):
            record = json.loads(line)
            # The dump's own stamp is itself capped by when the dump was taken.
            stamped = parse_update(record.get("latest_update") or "", observed)
            when = min(stamped, observed) if stamped else observed
            doc_id = record["doc_id"]
            if doc_id not in attested or when < attested[doc_id]:
                attested[doc_id] = when
    return attested


def pct(delta: float, base: float) -> float:
    return (delta / base * 100.0) if base else 0.0


def empty_stats() -> dict:
    return {**{k: 0 for k in STAT_KEYS}, "count": 0, "text_count": 0}


def load_sizes(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    sizes = {}
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        sizes[row["doc_id"]] = row
    return sizes


def bucket_key(when: datetime, granularity: str) -> str:
    return when.strftime("%Y") if granularity == "year" else when.strftime("%Y-%m")


def bucket_end(key: str, granularity: str) -> str:
    if granularity == "year":
        return f"{int(key) + 1:04d}-01-01T00:00:00Z"
    year, month = (int(x) for x in key.split("-"))
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return f"{year:04d}-{month:02d}-01T00:00:00Z"


def make_record(index: int, key: str, prev_key: str | None, granularity: str,
                cumulative_before: dict, bucket: dict, items: list[dict],
                total_items: int, partial: bool = False) -> dict:
    """`items` is the truncated display list; `total_items` is the real count."""
    after = {k: cumulative_before[k] + bucket[k] for k in cumulative_before}

    sizes = {}
    for k in STAT_KEYS:
        sizes[k] = {
            "old": cumulative_before[k],
            "new": after[k],
            "delta": bucket[k],
            "delta_pct": pct(bucket[k], cumulative_before[k]),
        }

    record = {
        "id": index,
        "date": bucket_end(key, granularity),
        "old_date": bucket_end(prev_key, granularity) if prev_key
                    else f"{key[:4]}-01-01T00:00:00Z",
        "period": key,
        "old": dict(cumulative_before),
        "new": dict(after),
        "sizes": sizes,
        "delta": {
            "count": bucket["count"],
            "count_pct": pct(bucket["count"], cumulative_before["count"]),
            "text_count": bucket["text_count"],
            "text_count_pct": pct(bucket["text_count"],
                                  cumulative_before["text_count"]),
        },
        # items_added is capped for file size; the counts are the real totals,
        # so the UI can say "showing 40 of 1427".
        "items_added": items,
        "items_added_count": total_items,
        "items_added_count_all": total_items,
        "items_added_truncated": total_items > len(items),
        "items_added_pct": pct(total_items, cumulative_before["count"]),
        "items_removed": [],
        "items_removed_count": 0,
        "items_removed_count_all": 0,
        "items_removed_pct": 0.0,
        # The site keeps only the latest touch per document, so a re-edit is
        # indistinguishable from a first publication. Everything lands in
        # items_added; nothing can be reported as "changed".
        "items_changed_count": 0,
        "items_with_changed_timestamp": 0,
        "all": {"old": dict(cumulative_before), "new": dict(after)},
    }
    if partial:
        record["sizes_partial"] = True
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=SITE_INVENTORY_PATH)
    parser.add_argument("--sizes", type=Path, default=SITE_SIZES_PATH)
    parser.add_argument("--catalogue", type=Path, default=None,
                        help="fold documents the catalogue lists but this "
                             "corpus lacks into a final counts-only bucket. "
                             "Off by default: meaningful for the snapshot, "
                             "which is 1254 documents behind the site, and "
                             "noise for our own fetch, which IS the catalogue.")
    parser.add_argument("--corpus-date", default=None,
                        help="ISO date the corpus was captured; caps every "
                             "`Latest update` above it as an upstream typo. "
                             "Defaults to the newest fetch in the journal.")
    parser.add_argument("--log", type=Path, default=TEXT_LOG_PATH,
                        help="fetch journal the corpus date is derived from")
    parser.add_argument("--attest", action="append", default=[],
                        metavar="PATH:YYYY-MM-DD",
                        help="an older dump's inventory and its capture date. "
                             "A document it holds cannot have arrived after "
                             "that date, whatever its `Latest update` now "
                             "says, so this pulls revised documents back "
                             "toward their real arrival year. Repeatable. Off "
                             "by default -- the curve is a lower bound "
                             "without it and a tighter one with it.")
    parser.add_argument("--out", type=Path, default=CHANGELOG_PATH)
    parser.add_argument("--granularity", choices=("year", "month"),
                        default="month")
    parser.add_argument("--max-items", type=int, default=40,
                        help="documents listed per period (all are counted)")
    args = parser.parse_args()

    if not args.inventory.exists():
        raise SystemExit(
            f"missing {args.inventory}; run `make parse-site` first "
            "(or `make snapshot-changelog` for the snapshot track).")

    if args.corpus_date:
        ceiling = datetime.fromisoformat(args.corpus_date)
        if ceiling.tzinfo is None:
            ceiling = ceiling.replace(tzinfo=timezone.utc)
    else:
        ceiling = corpus_date(args.log)

    records = [json.loads(l) for l in args.inventory.open(encoding="utf-8")]
    sizes = load_sizes(args.sizes)
    attested = load_attestations(args.attest)

    print(f"inventory: {args.inventory} ({len(records)} documents)")
    print(f"ceiling:   {ceiling:%Y-%m-%d} (later dates read as upstream typos)")
    if attested:
        covered = sum(1 for r in records if r["doc_id"] in attested)
        print(f"attested:  {len(attested)} documents in {len(args.attest)} "
              f"older dump(s), {covered} of them in this corpus")

    buckets: dict[str, dict] = defaultdict(empty_stats)
    listed: dict[str, list] = defaultdict(list)
    undated = 0

    pulled_back = 0
    for record in records:
        when = parse_update(record["latest_update"], ceiling)
        floor = attested.get(record["doc_id"])
        if floor is not None and (when is None or floor < when):
            # Attested earlier than it claims: an older dump held it. Counts a
            # document whose stamp is unparseable too -- presence is a date.
            if when is not None:
                pulled_back += 1
            when = floor
        if when is None:
            undated += 1
            continue
        key = bucket_key(when, args.granularity)
        measured = sizes.get(record["doc_id"], {})
        bucket = buckets[key]
        for k in STAT_KEYS:
            bucket[k] += measured.get(k, 0)
        bucket["count"] += 1
        if measured.get("content_bytes", 0) > 0:
            bucket["text_count"] += 1
        listed[key].append({
            "id": f"doc:{record['doc_id']}",
            "title": record["title"] or record["stem"],
            "date": when.strftime("%Y-%m-%dT00:00:00Z"),
            "new_bytes": measured.get("transliterated_bytes", 0),
        })

    intervals = []
    cumulative = empty_stats()
    prev_key = None
    for index, key in enumerate(sorted(buckets), start=1):
        items = sorted(listed[key], key=lambda i: i["date"])
        intervals.append(make_record(
            index, key, prev_key, args.granularity,
            dict(cumulative), buckets[key], items[: args.max_items], len(items),
        ))
        for k in cumulative:
            cumulative[k] += buckets[key][k]
        prev_key = key

    # Documents the live catalogue lists but the snapshot never had. They have
    # no measured bytes, so this interval reports counts only.
    if args.catalogue and args.catalogue.exists():
        known = {r["doc_id"] for r in records}
        live = [json.loads(l)["doc_id"] for l in args.catalogue.open(encoding="utf-8")]
        added = sorted(set(live) - known)
        if added:
            mtime = datetime.fromtimestamp(args.catalogue.stat().st_mtime,
                                           tz=timezone.utc)
            key = bucket_key(mtime, args.granularity)
            bucket = {**empty_stats(), "count": len(added)}
            items = [{"id": f"doc:{d}", "title": d.split("/")[-1],
                      "date": mtime.strftime("%Y-%m-%dT00:00:00Z"),
                      "new_bytes": 0} for d in added]
            intervals.append(make_record(
                len(intervals) + 1, key, prev_key, args.granularity,
                dict(cumulative), bucket, items[: args.max_items], len(added),
                partial=True,
            ))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(intervals, handle, ensure_ascii=False, separators=(",", ":"))

    print(f"periods:   {len(intervals)} ({args.granularity})")
    print(f"undated:   {undated} documents excluded (no parseable year)")
    if attested:
        print(f"pulled back: {pulled_back} documents bucketed earlier than "
              f"their `Latest update` claims")
    for rec in intervals[-6:]:
        print(f"  {rec['period']}: +{rec['items_added_count']:>5} docs, "
              f"cumulative {rec['new']['count']:>5}"
              f"{'  [counts only]' if rec.get('sizes_partial') else ''}")
    print(f"wrote:     {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
