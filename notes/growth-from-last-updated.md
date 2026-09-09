# Using `Latest update` as a growth series

Why this Atlas's growth chart is built from a field that does not mean what the
chart needs, and what was done about it. Figures here are illustrative — the
published ones are on the About page, live.

## The problem

sanskritdocuments.org publishes **no arrival date**. Each document carries only
`Latest update`, the most recent touch. A text encoded in 2004 and reproofed in
2023 reports 2023 and nothing else: its arrival is destroyed, not blurred. So
bucketing that field gives axis 1 (when was each text last touched), and using
it as axis 2 (how large was the collection at time T) understates early years
and overstates recent ones.

It is used as axis 2 anyway, because revision is rare enough — and because
attestation raises the floor where older observations exist.

## The revision rate is a property of the interval, not the corpus

Three observations exist: a 2020-06 site mirror (`parse_dump_2020`), the
Feb-2025 snapshot, and our own fetch. Comparing `latest_update` on documents
present in a pair:

    2020-06 -> 2025-02   15.4%  over 4.6y  =  3.33%/yr
    2025-02 -> 2026-08    1.7%  over 1.5y  =  1.16%/yr

The earlier interval revises about three times faster. **Do not quote a single
revision rate as a property of the corpus** — an older version of this note did,
and the figure it quoted was the quiet interval.

**Compare parsed dates, not raw strings.** Strings differ without the date
differing — whitespace, and appended second dates (`'January 01, 2005'` →
`'January 01, 2005, August 14, 2022'`, a real revision `parse_update` cannot
see, since it takes one date). String comparison gives 18.7%/2.4%; date
comparison 15.4%/1.7%. Both are defensible if labelled; **mixing them is not.**

Re-derive rather than quoting: compare `latest_update` across
`dump2020_inventory.jsonl`, `snapshot_inventory.jsonl` and
`site_inventory.jsonl`, keyed on `doc_id`.

## The error is directionally biased

Documents that do move, move far — median ~5 years, tail running 20–28. Every
revision moves a document *out of* an early bucket and *into* a recent one, so
the early years, where counts are smallest, lose the most proportionally. The
curve's shape survives; its 1990s values are a floor.

## Attestation: an older sighting raises that floor

`build_changelog --attest PATH:YYYY-MM-DD` treats **presence in an older dump as
a hard ceiling on arrival**. A document the 2020 mirror held existed by then
whatever its stamp now claims, and no later reproofing can lift that. The rule
is `min(latest_update, observed)`, so it never needs to know *which* dates are
wrong — only that a document was seen.

    make parse-dump-2020     # mirror -> data/dump2020_inventory.jsonl
    make changelog           # uses it automatically WHEN PRESENT

`make changelog` attests against **every older corpus present**, each guarded by
a `wildcard` so a missing one degrades instead of failing.

**An older sighting dominates a newer one**, since "existed by 2020" beats
"existed by 2025" wherever both apply — so the 2020 mirror does nearly all the
work, and adding the Feb-2025 snapshot moves the pre-2020 total by one document.
Expect any future dump to matter in proportion to its **age**, not its size.

The snapshot still earns its place elsewhere: it makes the revision rate a
*series* rather than a single interval, dates the disappearances, and is the
published cross-check track.

**What attestation does NOT fix**, all three stated on the About page:

- **Coverage is partial and uneven.** A reproofed document outside every older
  corpus is uncorrected, so two documents of the same true age are treated
  differently by an accident of what 2020 or 2025 happened to hold. Better in
  aggregate, *not* uniformly derived. Accepted deliberately.
- **It hardens one direction only.** A stamp that is wrongly *early* is
  invisible — nothing contradicts it. Only wrongly-late stamps get caught.
- **Date typos are unquantifiable.** A few documents carry a *later* date in the
  2020 mirror than today, a plain contradiction. That is a lower bound on
  corruption, not a census. Do not special-case any date string — `min()`
  already handles it.

## Empty periods are absent, not zero

`build_changelog` writes `sorted(buckets)`, and a bucket exists only if some
document landed in it — so a period with no documents is **missing from the
file**, not present with a count of 0.

Anything that treats row order as time will drift: the About chart once chose
x-axis labels by row index and gained a year at every hole. It now keys ticks
off the period's own calendar value (`docs/about.js`, `yearOf`/`yearsEvery`).
**Any future consumer — a sparkline, a parent-project series, a diff between
corpora — has to index by period or fill the gaps first.** Filling them in the
builder was rejected: a zero bucket also means "measured as zero", which is a
different claim from "no data".

## There is no system ID, and no third date signal

The sibling EBS Atlas gets two time signals — a roughly-chronological serial and
a timestamped image filename — so the obvious question is whether this corpus
exposes anything similar. **It does not.** Five places checked: the metadata
block (no ID or serial among any field), HTML attributes and comments (layout
ids only), `Indexextra` (prose), listing-page order (Spearman +0.058 against
date, signs both ways), and filename stems (disambiguators, not sequence).

**Why the analogy fails.** EBS is a database-backed catalogue: a system assigned
each record a serial and each scan a filename, both byproducts of ingestion.
This is a hand-maintained static site — a volunteer types an `.itx`, fills the
`%` header by hand, and it is copied into a directory. Nothing assigns identity;
the identifier *is* the human-chosen filename. That is also why the field has
typos a generated one could not (`Souce`, `La Jagattest update`, `August 43`).

Two machine-generated dates do exist — a page footer stamp and an HTTP
`Last-Modified` — but both describe the **file**, not the text, and neither
replaces `Latest update`.

## Open

- [ ] **Attrition as a series, not a sentence.** 204 documents in the 2020
      mirror are absent from our 2026 fetch: 25 relocated (same stem, new
      folder — `doc_vishhnu/gopigeeta` → `doc_giitaa`), 179 gone by stem. Only
      11 of the 204 survived into the Feb-2025 snapshot. **The growth curve is
      therefore net, not gross**, and nothing on the About page says so. A
      removals series is possible (`items_removed` already exists in the record
      shape and is always empty), but one observation cannot date a removal —
      only bound it to a 6-year window.
- [ ] Publish that this Atlas's series is `approximated`, not `measured`, so
      the parent can caveat per-series rather than blanket-disclaiming all
      three. (The transport question is settled: the contract was widened to
      read `changelog.json`, which `collect_atlas_growth.py` does.)
- [ ] `all_stats` here omits `last_changed` and `sized`, both of which we
      already compute. Verified still absent 2026-08-31.
