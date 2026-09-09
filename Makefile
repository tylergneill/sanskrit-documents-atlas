.PHONY: serve-fulltext parse parse-listings recount snapshot-tree \
        parse-site parse-listings-site build-catalogue count-sizes build \
        parse-scans check-scans changelog snapshot-changelog \
        parse-dump-2020 audit audit-update-about \
        serve serve-snapshot \
        fetch-metadata fetch-text extract-text free-server-port get-server-ip-address

# ============================================================================
# GROUP 1 -- the SNAPSHOT track.  A cross-check, not the product.
# ============================================================================
# These read an EARLIER Feb-2025 scrape of sanskritdocuments.org kept outside
# the repo (286M, see pipeline/config.py). 8547 documents, 18 months stale, and
# not ours. Never written to. Override with SDA_SNAPSHOT=/path or
# `make parse SNAPSHOT=/path`.
#
# Every target here writes a `snapshot_*` file and ends at `snapshot-tree`,
# which emits docs/data/snapshot_tree.json. It NEVER feeds `build`. Until
# 2026-08-18 it did -- `build` read the snapshot's inventory and sizes, so the
# published atlas was 18 months old while nothing said so.
#
# This whole group is deleted once the snapshot-vs-live diff is done.

# Docpages -> data/snapshot_inventory.jsonl (one record per text, no network).
parse:
	python -m pipeline.parse_snapshot $(if $(SNAPSHOT),--snapshot $(SNAPSHOT)) --report

# The 87 cached listing pages -> data/snapshot_listings.jsonl, recording which
# documents each page links. This is the third browse axis: multi-valued like
# `Category` but curated by the site, unlike it. Reads the snapshot, so no
# network -- `fetch-metadata` is the networked cousin that re-fetches these
# same pages live.
parse-listings:
	python -m pipeline.parse_listings $(if $(SNAPSHOT),--snapshot $(SNAPSHOT)) --report

# Docpage bodies -> data/snapshot_sizes.jsonl, in raw/content/IAST bytes.
# ~12s on 8 cores. Sizes are a pure function of the snapshot, so this only
# needs rerunning when the snapshot changes.
# Override worker count with e.g. `make recount WORKERS=4`.
recount:
	python -m pipeline.recount_sizes $(if $(SNAPSHOT),--snapshot $(SNAPSHOT)) $(if $(WORKERS),--workers $(WORKERS))

# ============================================================================
# GROUP 2 -- from the live site.
# ============================================================================
# The snapshot is 18 months old and the site has moved since. This checks what
# changed without re-downloading the corpus.
#
# *** THE TWO NETWORKED TARGETS. *** Both capped at 100 requests for this
# phase; neither will exceed that without a deliberate code change. One request
# per 2s, identified by a contact-bearing User-Agent.

# TIER 1 -- metadata. Sitemap + location pages + 87 category listings ->
# data/metadata_cache/{locations,listings}/ and data/catalogue.jsonl. ~88
# requests, and the thing to run first: the catalogue it emits IS the scrape
# list tier 2 walks.
#   make fetch-metadata
#   make fetch-metadata ARGS="--report"      # diff what's cached, no network
fetch-metadata:
	python -m pipeline.fetch_metadata $(ARGS)

# TIER 2 -- content. One request per document in the catalogue -> raw docpage
# HTML in data/fulltext_cache/<location>/<stem>.html. ~8547 requests, ~4.7h at
# the 2s delay. Resumable: a cached document is never refetched.
#   make fetch-text
#   make fetch-text ARGS="--limit 100"       # bounded first run
fetch-text:
	python -m pipeline.fetch_text $(ARGS)

# fulltext_cache -> data/text_extract/<location>/<stem>.txt, the cached pages
# with everything but the work's body stripped away. No network; reads the
# tier-2 cache off disk. Gitignored; this repo hosts no text.
#
# NEEDS the private `rivulet` package, which owns the extraction rules. Without
# it this EXITS 2 ("fulltext machinery not installed"), distinct from 1 =
# failure -- and every other target here is unaffected either way.
#   make extract-text
extract-text:
	python -m pipeline.extract_text $(ARGS)

# Scanned sources -> data/scans.jsonl + data/scans_rejected.jsonl. Reads the
# tier-1 cache off disk, so despite sitting in this group it costs no requests.
# Emits both halves on purpose: the keep rule is conservative (first
# parenthetical link only, scan-ish label, PDF target), and the rejects are
# where the next refinement comes from.
parse-scans:
	python -m pipeline.parse_scans $(ARGS)

# **NETWORKED, but not against sanskritdocuments.org.** Checks whether each
# distinct scan stem still resolves -> data/scan_liveness.jsonl. One request per
# STEM, not per link: 5073 links collapse to 891 books. ~30 min, because
# archive.org takes ~2s per HEAD -- the server sets the pace, not --delay.
# `build` reads the result and drops anything not live, so the interface and
# the exported pdf_count agree. Rerun after `parse-scans`; links rot.
#   make check-scans
#   make check-scans ARGS="--kind archive --limit 20"
check-scans:
	python -m pipeline.check_scans $(ARGS)

# ============================================================================
# GROUP 2b -- the REAL track, from our own fetch.
# ============================================================================
# The site-derived twins of group 1, reading data/fulltext_cache/ (9756
# documents, fetched 2026-08-11..15) instead of the snapshot. Same parsers --
# the page format is identical between the two corpora -- pointed at a
# different docroot and writing `site_*` files. No network.

# fulltext_cache -> data/site_inventory.jsonl (9756 documents).
parse-site:
	python -m pipeline.parse_snapshot --docroot data/fulltext_cache --out data/site_inventory.jsonl --report

# The 87 tier-1 listing pages -> data/site_listings.jsonl. The live pages, not
# the snapshot's copies of them.
parse-listings-site:
	python -m pipeline.parse_listings --listing-dir data/metadata_cache/listings --out data/site_listings.jsonl --inventory data/site_inventory.jsonl --report

# The cached listings -> data/catalogue.jsonl, the scrape list. NO NETWORK.
#
# `fetch-metadata` writes this too, as a side effect of its walk -- but that
# costs ~108 requests and needs rivulet, and every page it would re-request is
# already sitting in data/metadata_cache/listings/. Use this to repair a lost
# or truncated catalogue; use `fetch-metadata` when you actually want to see
# what the site says today.
build-catalogue:
	python -m pipeline.build_catalogue $(ARGS)

# fulltext_cache bodies -> data/site_sizes.jsonl, raw/content/IAST bytes. ~15s.
count-sizes:
	python -m pipeline.recount_sizes --docroot data/fulltext_cache --inventory data/site_inventory.jsonl --out data/site_sizes.jsonl $(if $(WORKERS),--workers $(WORKERS))


# What the source collection gets wrong, published to the About page.
#
# Never mutates anything: it reads, reports, and rewrites only its own region of
# docs/about.html between the AUDIT markers, plus the `data-stat` figures the
# hand-written prose tags. A finding is for a human to look at, never an
# auto-correction.
#
# **Offline, entirely.** Every check reads a file in data/, so there is no
# network and no exit-2 INCONCLUSIVE convention like the e-bharatisampat
# sibling has.
# Requires
# `parse-site`, `parse-listings-site`, `count-sizes` and `fetch-metadata`;
# `parse-scans`/`check-scans` are optional and their finding degrades to
# "not checked" rather than failing the run.
#
# Every number is re-derived by the run that publishes it. That is the whole
# point: the page quoted `shivarahasya` at 728 for as long as it was hand-typed,
# against a corpus that said 784.
#
# `--update-about` is strict in BOTH directions and exits non-zero on either --
# a data-stat tag naming a figure the audit does not compute, or a computed
# figure with no tag in the page. Neither is a silent skip, because a stale
# published number is exactly the failure this replaces.
#   make audit                  # report only, writes nothing
#   make audit-update-about     # ...and rewrite the About region
audit:
	python -m pipeline.audit $(ARGS)

audit-update-about:
	python -m pipeline.audit --update-about $(ARGS)

# ============================================================================
# GROUP 3 -- build and serve the site.
# ============================================================================

# Build docs/data/tree.json from OUR OWN fetch -- 9756 documents. Requires
# `parse-site`, `parse-listings-site` and `count-sizes`, and errors telling you
# which is missing. Quick (~2s); touches no source text.
#
# Also stamps docs/VERSION: `__content_version__` is derived from the newest
# `fetched_at` in text_fetch_log.jsonl, so the date the frontend shows is the
# date the corpus was actually scraped. It used to be hand-maintained and read
# 2025-02-16 for months.
build:
	python -m pipeline.build_tree $(ARGS)

# Build docs/data/snapshot_tree.json from the EARLIER Feb-2025 scrape --
# 8547 documents. Same shape as `build`, so the frontend reads either; they are
# alternatives, never combined, and the choice is made at serve time. Requires
# `parse`, `parse-listings` and `recount`. Does NOT stamp VERSION.
snapshot-tree:
	python -m pipeline.build_snapshot_tree $(ARGS)

# Parse the 2020 site mirror -> data/dump2020_inventory.jsonl. A DATING input,
# not a build track: nothing is served from it and no tree is built from it. It
# supplies `changelog` with the fact that a document existed by 2020-06-27,
# which is what pulls revised documents back toward their arrival year. Reads
# the mirror from SDA_DUMP_2020 or the default checkout. Local only.
parse-dump-2020:
	python -m pipeline.parse_dump_2020 $(ARGS)

# Build docs/data/changelog.json from each document's own `Latest update`,
# bucketed by MONTH -- OUR OWN fetch, 9756 documents. Needs `parse-site` and
# `count-sizes`. The upper bucket is capped at the newest `fetched_at` in
# text_fetch_log.jsonl, the same date `build` stamps as __content_version__.
# Local only, no network.
#
# Uses data/dump2020_inventory.jsonl as an arrival floor WHEN PRESENT, so the
# early years are not thinned by later reproofing (`make parse-dump-2020`
# writes it). Absent, the curve still builds -- just as the looser lower bound
# it was before. Pass ARGS="--attest ..." to add further dated dumps.
# Monthly is the published granularity, shared with the sibling atlases so
# sagara-sangama can plot all three on one time axis; pass year only for a
# quick local look, never for what ships.
#   make changelog
#   make changelog ARGS="--granularity year"
# Attest against every older corpus we hold. Order does not matter -- the
# earliest date wins -- and each is included only if it has been parsed.
# The 2020 mirror does nearly all the work (751 of 792 pull-backs): an older
# attestation dominates a newer one, since "existed by 2020" beats "existed by
# 2025" whenever both apply. The snapshot is kept in for the 41 documents it
# reaches that the mirror never held.
ATTEST := $(if $(wildcard data/dump2020_inventory.jsonl),--attest data/dump2020_inventory.jsonl:2020-06-27)
ATTEST += $(if $(wildcard data/snapshot_inventory.jsonl),--attest data/snapshot_inventory.jsonl:2025-02-16)
changelog:
	python -m pipeline.build_changelog $(ATTEST) $(ARGS)

# Build docs/data/snapshot_changelog.json from the EARLIER Feb-2025
# snapshot -- 8547 documents, capped at 2025-02-16, plus a final counts-only
# bucket for the 1254 documents the live catalogue lists and the snapshot never
# held. Needs `parse` and `recount`. Same shape as `changelog`, never combined
# with it; nothing serves this file, it exists for the snapshot-vs-live diff.
snapshot-changelog:
	python -m pipeline.build_snapshot_changelog $(ARGS)

# Serve docs/ locally on port 8003, gzipping JSON/JS/HTML/CSS.
# Same server, plus the extracted text at /text/<doc_id>, so each document
# gets a `txt` badge. LOCALHOST ONLY -- binds 127.0.0.1, and the text lives
# outside docs/ so no deploy can pick it up. Needs `make extract-text` to have
# run.
serve-fulltext:
	cd docs && python ../serve_docs.py --fulltext $(ARGS)

serve:
	cd docs && python ../serve_docs.py $(ARGS)

# Same server, but serving the snapshot tree at the frontend's tree.json URL --
# 8547 Feb-2025 documents instead of our 9756. A serve-time choice only: both
# builders always write their own file, and the frontend asks for the same path
# either way.
serve-snapshot:
	cd docs && python ../serve_docs.py --snapshot $(ARGS)

free-server-port:
	kill $$(lsof -ti tcp:8003)

get-server-ip-address:
	ifconfig | grep "inet " | grep -v 127.0.0.1
