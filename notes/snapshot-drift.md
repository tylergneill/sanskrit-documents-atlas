# snapshot drift

Evidence behind the Phase-2 comparison items in `scratch/todo.md` — the
Feb-2025-vs-live diff, and the 19 delinked documents.

The atlas is built from a Feb-2025 scrape. This note tracks how far
sanskritdocuments.org has moved since, measured two ways: a **catalogue diff**
(what documents exist) and a **metadata diff** (how existing documents changed).

## Catalogue: the site grew ~15% (measured 2026-08-11, 88 requests)

`make fetch-metadata` re-walked the sitemap and all 87 category listings —
87/87 returned HTTP 200 — and enumerated the documents they link.

**Re-confirmed 2026-08-15**, when tier 1 also fetched the 20 location pages for
the first time: the two indexes each enumerate 9781 documents with a symmetric
difference of zero, so the count below is corroborated along a second axis.

| | count |
|---|---|
| snapshot (`docpage_html_dls`) | 8547 |
| live catalogue | **9781** |
| added since Feb 2025 | **1254** |
| in snapshot, no longer linked | 20 |

**The nav caveat is spent (checked 2026-09-07).** These counts predated
`strip_nav`, so per-listing figures from that run were inflated by the dropdown
menu repeated on all 87 pages. `catalogue.jsonl` has since been rebuilt
(2026-09-04) and is clean: max 10 listings per document, nothing near the
87-page signature nav-linking leaves. The 9781 total was never affected.

**Do not read `catalogue.jsonl`'s mean of 2.28 listings per document as the
topic-axis figure.** It keeps all 87 slugs, so an alias pair double-counts —
`sanskrit_vishhnu` and `sanskrit_vishnu` both carry the same 1822 documents.
`site_listings.jsonl` is the deduplicated 85 and gives **2.08**, which is what
the atlas publishes.

**The atlas is missing about one document in eight.** Growth is concentrated in
the large deity collections — viṣṇu +417, śiva +265, devī +221,
misc/general +115, deities_misc +107 — with the rest in the low tens.

Of the 20 no longer linked, one is a case-only rename
(`svarNAkarShaNabhairavastotraM` → `...stotram`), leaving **19 genuinely
delinked**. Whether those pages still resolve is untested; they may be
unpublished, merged, or simply dropped from their listing.

### The snapshot was already incomplete in Feb 2025

Cross-checking the listings against what is on disk (offline, no requests)
found **43 documents that the Feb-2025 listings linked but the scrape never
saved**. Only 25 of those appear in the scrape's own `dl_errors.txt`; the other
**18 failed silently** — never downloaded, never logged.

So 8547 was never the true Feb-2025 total: the site indexed ~8590 then. This is
worth remembering whenever the snapshot is treated as a complete baseline.

**Confirmed independently 2026-08-12** by `make parse-listings`, which parses
the same cached listings offline and reports exactly 8590 distinct documents,
43 of them unheld — reached by a different route, with the nav stripped.

### Two catalogue entries are malformed at the source

    doc_z_misc_general/gharagharasanskRRitakAprachAra ho     (space in href)
    doc_z_misc_general/mahAbhAratagranthakavachamvAlmIkikRRitam.inf

Bad hrefs on the site's own listing pages, not parse errors — `.inf` and a
space-containing path are not documents. They inflate the live count by two.

## Metadata: 8 of 100 sampled

**Do not quote a drift rate from this.** 4 of 8 documents differed, all
genuinely, but the sample is tiny. The useful result is *what kinds* of change
occur.

### 1. Genuine growth and reproofing

`doc_shiva/dvinetrashambhustutiH` gained the tag `aShTaka`, and its
`Latest update` moved **November 9, 2018 → February 24, 2026**.
`doc_z_misc_shankara/bhagavanmAnasapUjA` gained `vishhnu`;
`doc_vishhnu/madanagopAlAShTakam` gained `vishnu`.

### 2. Email obfuscation — a site-wide policy change

    'PSA Easwaran psawaswaran at gmail.com'  ->  'PSA Easwaran psawaswaran'

Not per-document churn: one policy applied site-wide, which will diff on nearly
every document naming a proofreader (7447 of 8547). Left alone it drowns the
real signal — hence the normalization item in `scratch/todo.md`.

### 3. Orthographic normalization

    'vishnu'                    ->  'viShNu'
    'vishvanAthachakravartina'  ->  'vishvanAthachakravartin'

Tags are being regularized toward consistent ITRANS, and upstream is
mid-cleanup, so any category-count figure is a snapshot of work in progress.

**The three-distinct-tags problem is ours to absorb, and is (checked
2026-09-07).** `vishhnu`/`vishnu`/`viShNu` were three separate tags when this
was written. `pipeline/categories.py` folds them to one concept, and the
spelling that survives is **`vishhnu`** (1814 documents) — not `vishnu`, even
though `ALIASES` maps `vishhnu -> vishnu`. The alias sets the grouping *key*;
`canonical_spellings` picks the *display* spelling separately, and with both
being real slugs the majority wins. Do not read `ALIASES` as naming the
survivor.

The count is **317** canonical concepts from 366 raw spellings — re-derive
both rather than quoting them, the first from the inventory and the second from
its `.meta.json` sidecar.

## What a full metadata sample should report

- documents with **any** change (headline rate)
- documents whose **`Latest update` moved** (the real "text was revised" signal)
- category-only changes (curation, largely spelling)

treating `Proofread by` as noise until normalized — the site stripped addresses
from it site-wide, so it diffs almost everywhere without anything having
changed.

**No such sample is planned (2026-09-09).** The snapshot is kept as a dating
input for the changelog, not as a comparison corpus; this section records what
the measurement would have to control for, should the question ever come back.
