# sanskrit-documents-atlas

A more accessible interface for the text content at [sanskritdocuments.org](https://sanskritdocuments.org),
one of the [`Sāgarasaṅgama`](https://github.com/tylergneill/sagara-sangama) Atlases.

Indexes metadata and structure; hosts no text of its own. Every document links
back to sanskritdocuments.org for the content itself.

Served at https://tylergneill.github.io/sanskrit-documents-atlas.

Its [about page](https://tylergneill.github.io/sanskrit-documents-atlas/about.html)
is the user-facing documentation — what the collection is, how folders, topics,
categories and metadata fit together, and where the data is uneven.
`CLAUDE.md` has the architecture and data shape, and `notes/` the working
backlog and the evidence behind it. The rest of this file covers only how to
build it.

# how it works

A `pipeline/` emits `docs/data/tree.json`; a single-page frontend in `docs/`
browses it. The corpus is our own fetch of the site, kept outside the repo and
never written to.

## acquisition (not in this repo)

Everything that crosses the network lives in `rivulet`, a private package that
is not public and not obtainable. **A checkout without it cannot build the
corpus from scratch, and that is deliberate** — the acquisition code is the
only meaningful way to get the data, so these targets exit 2 ("machinery not
installed") with an explanation rather than half-running:

- `make fetch-metadata` — sitemap, location pages and category listings →
  `data/metadata_cache/` and `data/catalogue.jsonl`. ~100 requests. Run first:
  the catalogue it writes *is* the scrape list the next target walks.
- `make fetch-text` — one request per catalogued document → raw docpage HTML in
  `data/fulltext_cache/<location>/<stem>.html`. ~10k requests, so ~5h at the 2s
  delay; resumable, and a cached document is never refetched.
- `make check-scans` — scan-link liveness (archive.org, not
  sanskritdocuments.org).
- `make extract-text` — cached pages stripped to the work's body.

## building and serving

If `data/` is already populated, the rest of the pipeline runs offline and the
atlas builds normally:

- `make parse-site` — docpages → `data/site_inventory.jsonl`, one record per
  document
- `make parse-listings-site` — the cached listings → `data/site_listings.jsonl`,
  recording which documents each page links
- `make count-sizes` — docpage bodies → `data/site_sizes.jsonl`, in
  raw/content/IAST bytes
- `make build` — those three → `docs/data/tree.json`, and stamps
  `docs/VERSION` with the date the corpus was actually scraped
- `make changelog` — each document's own `Latest update` →
  `docs/data/changelog.json`, bucketed by month
- `make serve` — serve `docs/` on :8003

`build` errors and names whichever of its three inputs is missing. Byte counts
are a pure function of the corpus, so `count-sizes` caches them and `build`
never touches the source text — rerun `count-sizes` when the corpus changes, as
`build` trusts the cache and won't notice on its own.

Optional, and each degrades rather than failing the build:

- `make parse-scans` — scanned-source links → `data/scans.jsonl`, read off the
  metadata cache. `build` drops anything `check-scans` found dead, so the
  interface and the exported count agree.
- `make parse-dump-2020` — a dating input, not a build track. Gives `changelog`
  an arrival floor so early years aren't thinned by later reproofing.
- `make audit` / `make audit-update-about` — re-derives the figures published on
  the about page and rewrites only its own marked region. Every number is
  re-derived by the run that publishes it, so nothing on that page is
  hand-typed.

# parallel snapshot track

An earlier and smaller Feb-2025 scrape is still built by `snapshot-tree`,
`snapshot-changelog` and the `parse`/`parse-listings`/`recount` group, and
served by `make serve-snapshot`. They're alternatives to the main track, never
combined, and the choice is made at serve time. That whole group goes away once
the snapshot-vs-live diff is finished.

# license

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en),
matching `Sāgarasaṅgama`. Applies to this atlas's own code and derived metadata;
the texts themselves belong to sanskritdocuments.org and its contributors.
