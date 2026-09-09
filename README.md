# sanskrit-documents-atlas

A more accessible interface for the text content at [sanskritdocuments.org](https://sanskritdocuments.org),
one of the `Sāgarasaṅgama` Atlases.

Indexes metadata and structure; hosts no text of its own. Every document links
back to sanskritdocuments.org for the content itself.

# status: phase 1, built on a local snapshot

Built from **our own Feb-2025 scrape** of the site, kept outside the repo (286M)
and never written to. Unlike the sibling `e-bharatisampat-atlas`, the input here
is neither borrowed nor partial: 8547 documents with full text and metadata,
which is essentially the whole collection.

The snapshot is 18 months old, which is the one real caveat, and the gap is now
measured rather than guessed at. Re-walking the site's own category listings
(88 requests) puts the live collection at **9781 documents against our 8547** —
so roughly **one in eight is missing here**, concentrated in viṣṇu, śiva, and
devī. Twenty went the other way and are no longer linked. The Feb-2025 scrape
was also never quite complete: it saw ~8590 documents and saved 8547, logging
only 25 of the 43 misses. See `notes/snapshot-drift.md`.

Independent re-acquisition is **built, authorized, and done**: `make
fetch-metadata` enumerated the live corpus (9781 documents as of 2026-08-15)
and `make fetch-text` fetched **9756 of them (315 MB)** — the remaining 25 are
links the site no longer serves.

# what's in it

8547 documents, filed two independent ways:

- **by collection** — the canonical placement, 20 directories. Mostly by deity
  (devī, śiva, viṣṇu, gaṇeśa … ~7000 documents) but not uniformly: veda,
  upaniṣad, purāṇa, yoga and several *misc* buckets are genre divisions no deity
  governs.
- **by category** — the cross-listing facet: 332 tags, ~3.1 per document, 26718
  placements, so the same text is reachable under each of its tags.

Corpus totals come from the collection axis, which counts each document exactly
once. 209 MB of Devanagari text (113 MB transliterated to IAST); the median
document is ~5 KB, while the Purāṇas and Monier-Williams run past 4 MB each.

Figures are measured from the current snapshot — re-derive rather than quoting
them.

# how it works

A `pipeline/` emits `docs/data/tree.json`; a single-page frontend in `docs/`
browses it.

- `make parse` — docpages → `data/snapshot_inventory.jsonl`, one record per
  document, no network
- `make recount` — docpage bodies → `data/snapshot_sizes.jsonl`, measuring every
  document in raw/content/IAST bytes (~12s)
- `make build` — inventory + sizes → `docs/data/tree.json` (~1s)
- `make changelog` — each document's own `Latest update` →
  `docs/data/changelog.json`, 34 yearly buckets from 1992
- `make serve` — serve `docs/` on :8003
- `make fetch-metadata` — **NETWORKED.** sitemap + 87 listings + 20 location
  pages → `data/metadata_cache/{listings,locations}/` and
  `data/catalogue.jsonl` (9781 documents). ~108 requests
- `make fetch-text` — **NETWORKED.** every document in the catalogue → raw
  docpage HTML in `data/fulltext_cache/<location>/<stem>.html`. ~9781 requests,
  ~5.4h at the 2s delay; resumable, and a cached document is never refetched

Byte counts are a pure function of the snapshot, so they're measured once by
`recount` and cached. `build` reads that cache and never touches the source
text, which is why it's fast. Rerun `recount` when the snapshot changes; `build`
trusts the cache and won't notice on its own.

See `CLAUDE.md` for architecture and data shape, and `notes/` for the working
backlog and the evidence behind it.

# license

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en),
matching `Sāgarasaṅgama`. Applies to this atlas's own code and derived metadata;
the texts themselves belong to sanskritdocuments.org and its contributors.
