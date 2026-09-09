# sanskrit-documents-atlas

A browsable atlas over the **sanskritdocuments.org** corpus, one of the
`sagara-sangama` atlases. A `pipeline/` emits `docs/data/tree.json`; a
single-page frontend in `docs/` browses it.

This repo **hosts no text of its own.** It indexes metadata and structure and
links out to sanskritdocuments.org.

## `notes/` — structure, research, and tasks in flight

**The shape is the same in all five repos:**

    notes/*.md        non-trivial notes on structure -- why it is built this
                      way, what will bite you. NOT a record of how a decision
                      was reached or what the state of play was on some date.
    notes/<topic>/    folders of research material: samples, one-off analysis
                      scripts, measurements kept so a figure can be re-derived
                      rather than re-guessed. Each carries its own README.
    notes/scratch/    tasks in flight -- plans, scoped designs, measurements
                      under way, and the backlog itself.

**The lifecycle.** A new task is written into `scratch/`. When it finishes, any
insight worth keeping is **promoted** into a top-level note (or into a code
comment beside the thing it explains) and **the scratch file is deleted**.
Nothing is kept because it was expensive to write.

Keep top-level notes short. A long one usually means a task's history was never
cut out of it.

### When asked what's left

On "what do the notes say we need to work on" (or any variant — "what's next",
"what's still open"), **read the notes and answer from them.** Don't guess from
code or git history.

1. `notes/scratch/todo.md` is the spine — every open `- [ ]` item. Start there.
2. Everything else under `scratch/` is a task in flight; check its status line,
   and check it against the code before acting on it.

### Chipping away

- **Check the box** (`- [ ]` → `- [x]`) when an item is done, and say so.
- **Delete a note file once everything it covers is resolved** — that is the
  intended end state.
- **Add what you learn.** New constraint, new open question → it goes in the
  relevant note with the detail needed to act on it later. Findings that close a
  question can be recorded as closed (see `snapshot-drift.md`, where a suspected
  parse bug was checked and cleared) so nobody re-opens them.
- **Don't cite a notes figure as fact — re-derive it.** Several are measurements
  of a snapshot that will be replaced.

## The data underneath

**The older corpora live together outside the atlas**, under
`sagara-sangama/third_party_dumps/sanskrit-documents/` (consolidated there
2026-08-20):

    2025-my-own-dump/
        docpage_html_dls/    8547 document pages -- the Feb-2025 scrape
        subpage_html_dls/    87 listing pages
    2020-sanskrit-documents-dump/
        sanskritdocuments.org/   2020-06-27 `wget -r` mirror of the whole site

Both are read-only: nothing writes to them, none of it is committed. Paths
derive from `_DUMPS_ROOT` in `pipeline/config.py`, so the layout is stated once;
override the root with `SDA_DUMPS`, or either corpus individually with
`SDA_SNAPSHOT` / `SDA_DUMP_2020` (or `--snapshot` / `--dump`).

**Both older corpora are the author's own**, despite living under
`third_party_dumps/` (the 2020 mirror genuinely is someone else's; the directory
is named for the general case). The Feb-2025 scrape is an *earlier, less mature
pass* by the same person who wrote this pipeline -- **not third-party**, and
older wording calling it that is wrong. What makes it a cross-check rather than
the product is its age and method, not its provenance.

Its `metadata_master.csv` was left behind when the corpus was consolidated;
**we re-derive from the HTML rather than trusting the CSV**, since the HTML is
primary and carries fields the CSV dropped.

That earlier pass also produced a scraping notebook, `scrape_and_parse.ipynb`,
kept outside this repo. **Read it before changing extraction logic** — it is the
record of how the corpus was obtained and how its pages are shaped. It is where
`div id="article"` comes from; guessing that container by analogy with the
sibling atlas (`div id="Body"`) matches nothing here.

## Two axes and a filter

Unlike the sibling atlases this corpus has **no single hierarchy**, and the tree
reflects that with two sibling branches:

- **folders** — the canonical `Location`, one document in exactly one node.
  Mostly deity (devii, shiva, vishhnu, … ~7000 docs) but *not uniformly*:
  veda, upanishhat, purana, yoga and the `z_misc_*` buckets are genre divisions.
  Calling this axis "by deity" would misfile the Vedas.
- **topics** — the site's own 87 browsable pages at `/sanskrit/<slug>/`,
  from `make parse-listings`. Multi-valued (2.08 pages per document) but
  *curated by the site*, which makes it the honest cross-cutting axis.
  **That mean is 2.28 before alias suppression** — `catalogue.jsonl` keeps all
  87 slugs, so a document on `/sanskrit/vishhnu/` is counted again under
  `/sanskrit/vishnu/`. `site_listings.jsonl` is the deduplicated 85 and is what
  the tree is built from. Quote 2.08; the higher figure double-counts the
  site's own aliases.

Renamed from "by collection"/"by listing" on 2026-08-24: the folder is a real
server directory and "topic" is what the `/sanskrit/<slug>/` pages are, so both
labels now say what the thing is. **Sweeping a rename: collect from rendered output, not from source.** Three
passes were needed in 2026-08-25 because the first two grepped for the words
expected to appear. What worked: strip tags and collect
`\w*(locat|listing)\w*` from the rendered text of each output surface. The
stragglers all hid where a prose grep misses.

**The `data-stat` keys followed on
2026-08-25** — `locations*` → `folders*`, `listing_pages*` → `topic_pages*`,
`listed`/`unlisted` → `on_topics`/`off_topics`, `mean_listings`/`max_listings`
→ `mean_topics`/`max_topics`. Because the tag is a two-way contract, a key
rename is one edit touching `intro_stats()` and every tag site together;
renaming on one side alone fails the run.

**Both branches are flat.** `Location` was briefly subdivided by `Sublocation`,
but that field just repeats the location for ~99% of documents and every value
that differed was upstream noise — see the 2026-08-24 entry in `notes/scratch/todo.md`.
Because nothing nests, the sidebar has no disclosure column at all; restoring
depth to either branch means restoring the arrow in `renderSidebarNode`.

**Browse nodes link out, and their URLs are derived, not stored.** `rehydrate()`
maps `loc:doc_devii` → `/doc_devii/` and `lst:ashtaka` → `/sanskrit/ashtaka/`,
the same size discipline as document URLs.

**Every node counts DISTINCT documents**, via `build_tree.distinct_stats()`, and
branch totals are the union of their members. Summing per-placement stats is
what produced the old "26718 texts" bug; do not reintroduce it by rolling these
branches up with `roll()`. `all_stats` is the folders branch's.

Topic nodes carry bare `{id, title, ref}` entries that the frontend
rehydrates from the folders branch — see `rehydrate()` in `docs/app.js`,
which resolves any node with a `ref` generically.

**Reading a listing page: cut the nav first.** The site's dropdown menu sits in
`<nav>`, is repeated verbatim on all 87 pages, and links documents directly, so
scraping the whole page files those under every listing. `parse_index.
strip_nav()` is the shared cut, used by both the offline and networked halves —
and it is *why* `parse_index.py` stayed public when fetching moved to rivulet:
`parse_scans` and `parse_listings` need it with no network and no rivulet.

Only one axis is on screen at a time — a segmented control in the topnav, with
`activeBranch()` standing in for the tree root throughout `app.js`.

**`Category` is a filter, not a browse axis** (since 2026-08-13). It was a third
branch until then, and it was the wrong shape: the field is uncontrolled free
text mixing genres with author names and typos, so rendering it as a hierarchy
of some three hundred peers implied a taxonomy that does not exist — and
rolling it up produced the 26718 double-count. The filter reads each page's
`meta.categories`, ANDs its rows, and has no rollup, so that class of bug cannot
recur. Grouping the tags by type was tried and rejected; see
`notes/scratch/category-groups-tentative.md`.

Two things to know before touching it:

- **`visibleBranch()` is the single source of truth for what is on screen.**
  Both `renderSidebarTree` and `renderMain` read through it, so their stats can
  never disagree. It filters, then **restats every surviving node**
  (`restatFiltered`) — without that a filtered node keeps the pipeline's
  unfiltered stats and the sidebar reports the whole corpus beside three rows.
- **That restat dedups per node, not branch-wide.** A single shared "already
  counted" set credits each document to whichever node is visited first and
  renders every later node as `0 texts`. On the listing axis, where a document
  sits on 2.08 pages, that emptied 35 of 40 nodes. Each node counts its own
  members in full; only the branch total is a union.

## tree.json is size-sensitive

The frontend loads the whole file, so the build omits everything derivable:
document `url` (always `<base>/<doc_id>.html`), download hrefs (a per-format
suffix on that path), and per-page stats in the listing branch. Reconstituted
client-side in `rehydrate()`. Undoing any of these takes the file from 9.8 MB
back toward 41 MB. (Retiring the category branch took it 13.5 MB → 9.7 MB; the
scan links added since brought it back to 11.4 MB, and dropping unread metadata
on 2026-09-07 took it to 9.8 MB.)

**`meta` carries only what `app.js` reads.** Six fields — `language`, `subject`,
`texttype`, `proofread_by`, `transliterated_by`, `description` — shipped on
every document until 2026-09-07 with no code path reading any of them: 1.6 MB,
14% of the file. They remain in `site_inventory.jsonl`, which is what the
audit's coverage table counts, so the atlas knows them and simply stops mailing
them to readers. Restoring one is a line in `build_tree.make_page` **plus the
code that renders it, in the same change**. `subject` should stay out
regardless: 92% of documents carry the single value
`philosophy/hinduism/religion`, so it separates nothing.

**That split is what lets the inventory grow freely.** On 2026-09-07 nine more
`inf` fields were extracted — `subdeity`, `indexextra`, `acknowledge_permission`,
`source`, `translated_by`, `subcategory` and three typo-key folds — and
`tree.json` grew by 20 bytes, all of them one recovered `meta.updated`. New
fields go to `site_inventory.jsonl` and the audit's coverage table reads them
there; `make_page` enumerates `meta` explicitly, so nothing can leak into what
readers download. Adding a field is cheap *because* shipping one is not.

**A derived field can pay for itself.** `Latest update` ships as `meta.updated`
(`YYYY-MM`), parsed in the pipeline rather than shipped as the site's free text
— 148 KB of raw strings became 67 KB, so the atlas got dates and the file got
138 KB *smaller*. Day precision is dropped because nothing renders it.

## Category normalization happens in the pipeline, never the frontend

`pipeline/categories.py` folds the free-text `Category` field to canonical
concepts, and `parse_snapshot.collect` applies it to every record. `docs/app.js`
treats `meta.categories` as already-canonical: it never folds, aliases, or
de-duplicates. Add a variant to `ALIASES` and it disappears from the filter on
the next `make parse && make build`, with no frontend change.

**Which spelling survives**: the slug spelling where one exists, else the
majority. This is a display decision — the survivor is what the filter offers as
an option — so getting it backwards shows a spelling almost no documents use.

**366 raw spellings → 317 concepts**, of which 87 name a real listing page.
Both halves are published figures: the fold is lossy, so `parse_snapshot`
counts the raw spellings before folding and writes them to a sidecar
(`<inventory>.meta.json`) that `intro_stats()` reads — the folded inventory
cannot answer it.

The guard in `build_key` keeps `gita`/`giitaa` and `vishhnu`/`vishnu`/`vishnu_misc`
distinct because those are separate pages the site maintains on purpose; the
**87/87 slug round-trip is the check** that a new fold has not merged two real
slugs. Re-run it whenever `ALIASES` or `mechanical()` changes.

## Commands

| Command | Does |
|---|---|
| **SNAPSHOT track** | *earlier Feb-2025 scrape, 8547 docs — a cross-check, not the product* |
| `make parse` | snapshot docpages → `data/snapshot_inventory.jsonl` (no network) |
| `make parse-listings` | the snapshot's 87 listing pages → `data/snapshot_listings.jsonl` |
| `make recount` | snapshot bodies → `data/snapshot_sizes.jsonl` (~12s) |
| `make snapshot-tree` | those three → `docs/data/snapshot_tree.json` |
| `make snapshot-changelog` | snapshot `Latest update` → `docs/data/snapshot_changelog.json` (unpublished) |
| **REAL track** | *our own 2026-08 fetch, 9756 docs* |
| `make parse-site` | `fulltext_cache/` → `data/site_inventory.jsonl` (no network) |
| `make parse-listings-site` | tier-1 listing cache → `data/site_listings.jsonl` |
| `make build-catalogue` | tier-1 listing cache → `data/catalogue.jsonl`, no network (repairs it without refetching) |
| `make count-sizes` | `fulltext_cache/` bodies → `data/site_sizes.jsonl` (~15s) |
| `make build` | those three → `docs/data/tree.json`, and stamps `docs/VERSION` |
| `make parse-dump-2020` | 2020 site mirror → `data/dump2020_inventory.jsonl` (dating input, not a track) |
| `make changelog` | `Latest update` per document, floored by the 2020 mirror → `docs/data/changelog.json` |
| `make audit` | all six checks → a report; writes nothing. Entirely offline — no network, no rivulet |
| `make audit-update-about` | ...and rewrite the About page's audit region and every `data-stat` figure |
| `make serve` | serve `docs/` on :8003 |
| `make fetch-metadata` | **networked, needs rivulet** — tier 1: sitemap + 87 listings + 20 locations → `data/metadata_cache/{listings,locations}/` + `catalogue.jsonl`. ~108 requests |
| `make fetch-text` | **networked, needs rivulet** — tier 2: every document in the catalogue → `data/fulltext_cache/<location>/<stem>.html`. ~9781 requests, ~5.4h |

## The About page's figures are generated, not typed

`docs/about.html` carries no hand-written numbers. Every figure sits in a
`<span data-stat="key">`, and `make audit-update-about` rewrites the digits from
`data/` at build time — there is no runtime fetch and no JSON, so the page is
correct with JS disabled.

**The tag is the contract, and it is strict in both directions.** A tag naming a
stat `intro_stats()` does not compute is a hard error; a computed stat with no
tag in the page is *also* a hard error. Neither is a silent skip, because a
stale published figure is exactly what this replaces — the page quoted
`shivarahasya` at 728 for as long as it was hand-typed, against a corpus that
said 784. So prose around a tag can be rewritten freely, but deleting a tagged
sentence means dropping its key from `intro_stats()` in the same change.

Formatting is carried by the *type*: an `int` gets thousands separators, a
`float` one decimal, and a `str` passes through untouched (used where two
decimals matter, as for `mean_listings`). A figure that wants a whole number
says so by being an int at the computation site, never by loosening `_fmt`.

Anything published here that also appears in `tree.json` must be derived the
same way — `audit.py` intersects scan liveness with `scans.jsonl` and skips
empty `doc_id`s precisely because `build_tree` does, and a page disagreeing with
the tree it ships beside is the drift this exists to prevent.

## What to carry between machines

`data/` is gitignored, so moving work means copying it by hand. Only the two
site-derived caches are expensive; everything else rebuilds locally in seconds.

    data/metadata_cache/    108 requests -- the index, and the scrape list
    data/fulltext_cache/    9756 documents, 315 MB, ~5.5h -- the corpus itself

**The cache is the resume state.** Unlike the sibling atlas, there is no cursor
to carry: `fetch_text` treats "file on disk" as "done", so the journal
(`data/text_fetch_log.jsonl`) is a record, not resume state, and a run resumes
correctly from the cache alone. Writes go through a `.part` rename so a crash
cannot leave a truncated page that reads as complete.

Everything else — `catalogue.jsonl`, `snapshot_inventory.jsonl`,
`snapshot_listings.jsonl`, `snapshot_sizes.jsonl` — is a pure function of those
plus the snapshot, and is cheaper to regenerate than to copy.

**`catalogue.jsonl` included: `make build-catalogue` rebuilds it from
`metadata_cache/listings/` with no network.** It is *also* written by
`fetch_metadata`, as a side effect of the tier-1 walk, and for a long time that
was the only thing that wrote it — so a truncated catalogue looked like it
needed a ~108-request refetch of 87 pages already on disk. It does not. Reach
for `fetch-metadata` when you want to know what the site says *today*; reach for
`build-catalogue` when you just want the file back. The parse half is imported
from `parse_index.py`, never reimplemented, so the scrape list cannot drift from
what the fetchers believe the site holds.

`build` requires `parse-site`, `parse-listings-site` and `count-sizes`, and
errors telling you which is missing; `snapshot-tree` requires the snapshot
three. **It trusts the size cache and cannot tell it is stale**, so whatever
updates the snapshot is what reruns `recount`.

`make serve` will silently serve *another repo's* `docs/` if port 8003 is
already held — check with `make free-server-port` when the data looks wrong.

## Two build tracks, never combined

**`build` reads our own fetch; `snapshot-tree` reads the Feb-2025 scrape.**
They write different files and are alternatives, and which one the frontend
gets is a **serve-time** flag (`make serve-snapshot`), never a build-time one.

    build               site_inventory + site_listings + site_sizes  -> tree.json                9756 docs
    snapshot-tree       snapshot_* equivalents                       -> snapshot_tree.json       8547 docs
    changelog           site_inventory + site_sizes                  -> changelog.json           9756 docs
    snapshot-changelog  snapshot_* equivalents                       -> snapshot_changelog.json  8547 docs

This separation dates from 2026-08-18. Before it, **`build` read the snapshot's
inventory and sizes** — so the published atlas was an 18-month-old earlier
scrape while everything around it implied otherwise. The tell was the topbar
datestamp reading `2025-02-16` long after our own fetch had completed.

The same parsers serve both corpora: the page format is identical, so
`parse_snapshot` and `recount_sizes` take a `--docroot` and `parse_listings`
takes a `--listing-dir`. No parsing logic is duplicated, and
`build_snapshot_tree` is a thin wrapper over `build_tree` with different
defaults.

## The datestamp is derived, never hand-written

`build` stamps `docs/VERSION` — `__content_version__` from the newest
`fetched_at` in `data/text_fetch_log.jsonl` (the scrape records its own date),
`__data_version__` from today. **`snapshot-tree` does not stamp it**, since the
snapshot must never relabel the site's currency.

If the topbar date looks wrong, the fix is in the journal or the builder, not
in `docs/VERSION` — editing that file by hand is what let it sit at
`2025-02-16` for months.

## The changelog is growth, not revision history

`make changelog` buckets documents by their own `Latest update` (9754 of 9756
parse; the field is free text and needs a forgiving parser — abbreviated months,
`Julu`, `August 43`, `11-Feb-2015`). **The site keeps only the most recent touch
per document**, so a text encoded in 2004 and reproofed in 2023 appears once,
under 2023. Don't describe this as a revision history.

**Since 2026-08-20 the real track floors those dates against a third corpus**, a
2020-06-27 site mirror (`make parse-dump-2020`, 4739 docs). Presence in it proves
a document existed by then whatever its stamp claims, so `build_changelog
--attest` buckets it by `min(latest_update, 2020-06-27)`. That pulls 751
documents back and lifts the pre-2020 collection 19.2%. A bucket now means
"documents known to exist by then" — closer to real growth than "last touched on
or before then" was, and still a lower bound, since the mirror covers 4535 of
9756 and only catches stamps that are wrongly *late*.

**The mirror is a dating input, not a build track.** Nothing is served from it,
no tree is built from it, and `snapshot-changelog` does not use it — the
snapshot must keep reporting what the snapshot alone can support. The Makefile
passes `--attest` only when `data/dump2020_inventory.jsonl` exists, so a machine
without the mirror still builds, just to the looser bound.

**It is two-track like `build`**, and became so on 2026-08-19 — the 2026-08-18
split covered the tree and missed this. Until then the published curve was the
snapshot's: 8547 documents ending Feb 2025, with the 1254 our own fetch already
held bolted on as a final counts-only bucket dated from `catalogue.jsonl`'s file
mtime. It read as growth, which is why it survived the tree's migration.

**The date ceiling is per-track and cannot be a constant.** Every `Latest
update` above the date the corpus was captured is an upstream typo (two exist,
2027 and 2029) and is clamped to it. The snapshot's ceiling is 2025-02-16; ours
comes from the newest `fetched_at` in `text_fetch_log.jsonl` — the same source
`build` stamps `__content_version__` from, so the chart's last bucket and the
topbar date cannot drift apart. Hardcoding the snapshot's date rewrites all 386
genuinely-2026 documents back into February 2025.

`--catalogue` folds documents the live catalogue lists but the corpus lacks into
a final `sizes_partial` bucket. **On by default only for the snapshot**, which
is 1254 documents behind; on the real track the corpus *is* the catalogue and
the residue is just the 25 documents the site 404s.

## Clean-text output lives in rivulet

**This repo's pipeline is unchanged.** Unlike the other two atlases, nothing
moved out of it: its metadata (`<pre class="inf">` — title, author, categories,
`latest_update`) exists *only inside the fulltext pages*, and the listing pages
carry just a doc_id and a Devanāgarī title. So the public pipeline keeps
fetching whole pages, exactly as before.

What `rivulet` adds is one thing this repo never did: **body-only plain text**.

    make extract-text

`pipeline/extract_text.py` resolves the paths and calls in; `pipeline/fulltext.py`
is the guarded import, and **exits 2** ("fulltext machinery not installed") when
rivulet is absent — distinct from 1 = failure, the same shim the other two
Atlases use. Nothing else here imports rivulet, and every other target runs
without it.

It writes `data/fulltext_cache/` (what the site served) -> `data/text_extract/`
(clean plain text), the same two directories every Atlas uses. Both are under
the gitignored `data/`; this repo still publishes no text.

**The output is IAST**, matching `recount_sizes.py` — which derives
`transliterated_bytes` from this same body — so the text on disk and the byte
figure the tree publishes are in one script. Verified equal on a sample: 57,986
Devanāgarī bytes and 48,795 IAST bytes from both paths. `--no-transliterate`
writes Devanāgarī instead, for a machine without rivulet's `[translit]` extra.

The page holds two `<pre>` blocks and only one is the work:

    <PRE itemprop="text" class="stotra" id="content" lang="sa">   the text
    <pre class="inf">                                             the metadata

Selected by **`id="content"`, not by class** — the class varies (`stotra` 9528,
`vedic` 157, `shobhika` 68, `namavali` 1) while the id is on all 9754 of the
9756 cached pages. The two without one
(`doc_devii/siddhasarasvatIstotram2`, `doc_vishhnu/viShNorapAmArjanastotram`)
are genuine metadata-only stubs, reported as such rather than raised on.

The `inf` block is **excluded by selection, never stripped afterwards** — the
metadata is never in hand, so no later change can start leaking
`% Send corrections to` lines into published text.

## rivulet holds everything networked (since 2026-09-03)

**This repo can no longer fetch anything on its own, and that is deliberate.**
Both fetch tiers and `check_scans` moved to the private
`rivulet` package. What stayed is everything that reads a cache already on
disk: all parsing, sizes, trees, the changelog, and the audit.

Two shims name rivulet, and nothing else does:

    pipeline/fetch.py      acquisition + the networked checks
    pipeline/fulltext.py   clean-text extraction

Both import at the point of use and **exit 2** ("machinery not installed"),
distinct from 1 = failure.

**The command surface did not change.** `pipeline/fetch_metadata.py`,
`fetch_text.py` and `check_scans.py` still exist as thin runners, so every
`make` target and every `python -m pipeline.<name>` works as before.

**`parse_index.py` is the seam.** The old `fetch_metadata` held both the
network walk and the pure link parsing; only the walk left. `strip_nav`,
`subpage_links`, `docpage_links`, `doc_id_of`, `SITE_BASE` and `USER_AGENT` are
public in `pipeline/parse_index.py`, and rivulet imports them back — the
allowed direction. Moving them would break `parse_scans` and `parse_listings`
on a checkout with no rivulet.

## Before fetching anything

**The 100-request phase cap was lifted 2026-08-13.** There is no ceiling in the
code any more: `--limit` bounds a single run and nothing refuses a larger
number. Bulk re-acquisition is authorized and no longer needs asking about.

**Acquisition is two tiers, and they do not compare anything.** `fetch_metadata`
builds the scrape list; `fetch_text` walks it. Diffing the result against the
Feb-2025 snapshot is a separate, later question — keep it out of the fetchers.
Both now live in `rivulet/extract/sanskrit_documents/`; the terms below travel
with them and are restated in rivulet's own README.

What replaces the cap is **rate, not budget** — the constraint that was always
doing the real work. Every fetcher stays single-threaded, one request per
`--delay` (default 2s) measured start-to-start, with a contact-bearing
User-Agent, backing off and stopping on 429/5xx rather than retrying into a
wall. Keep those properties in anything new; they are the terms, not the cap.

