# todo

The spine of the backlog. Every open item lives here, grouped by phase; the
other files in `notes/` are the evidence behind these items, not separate lists.

## Phase 1 — browsable interface over the snapshot

- [ ] **The source's identifiers are not in any transliteration scheme, and
      one claim in the notes said they were.** Raised 2026-08-23. `vishhnu` is
      not ITRANS — proper ITRANS is `viShNu`; the site simply made the spelling
      up. Measured over the 9680 documents with a `title_deva`: real ITRANS
      reproduces the stem **332 times, 3.4%**. The site cannot write
      ñ/ṅ at all (`~n`/`~N` appear in **zero** of 9756
      stems, so `पञ्च` flattens to `pancha`, losing the nasal on 232
      documents), writes `shh` for ṣ (32 stems, 2 tags covering 2064 documents,
      3 of the 20 locations), and `ksh` for kṣ (43 stems, 6 tags, 224
      documents).
      **Checked, and nothing is currently being corrupted**: `ensureSchemeCached`
      in `docs/app.js` converts only `title_deva` and falls back to the raw
      label, and the category filter renders tags as plain strings. But that was
      true by luck of implementation, not because it was written down. It is
      written down now, in `site-structure.md` (which previously claimed
      outright that `Sanscript.t(title_deva, "devanagari", "itrans")` reproduces
      the stem — it does not).
      **The About page no longer carries it** (2026-08-27): the paragraph
      quoting the round-trip was cut in an editing pass, and because a computed
      stat with no tag is a hard error, `itrans_exact`/`itrans_exact_pct` and
      `itrans_roundtrip()` came out of `audit.py` with it. The 3.4% above is
      therefore a measurement in this note, not a published figure — re-derive
      it rather than citing it; the helper is recoverable from git history if
      the figure is ever wanted back.
      **Half closed 2026-09-07.** The downstream half is now settled by
      construction: `tree.json`'s `meta` carries only `doc_id`, `title_deva`,
      `categories`, `downloads`, `updated`, `scans` and `author`, because the
      six unread fields were dropped — `texttype` and `proofread_by` among them.
      So no consumer *can* transliterate them; they are not shipped. The two
      `Sanscript.t` call sites in `app.js` take `title_deva` and node titles
      only, and `translitTextUncached` no-ops on non-Devanāgarī input.
      **Still open**: whether the site's own `Proofread by` / `Texttype` /
      `Indexextra` prose carries the made-up spellings. That is a question about
      the source, answerable offline from `site_inventory.jsonl` (which still
      holds all six fields), and it matters only if those fields are ever
      surfaced.

- [ ] The 19 documents in the snapshot but no longer linked live — are they
      unpublished, merged, or just delisted? ~19 requests, now unblocked.
- [ ] **Decide on the third-party PDFs.** 70 survive the liveness check, but
      they are the weak tier: **a third were already dead (65.4% live, 70 of
      107)** against 91.2% for archive.org and 92.0% for the site's own
      `scannedbooks`. Still unverified as *scans* — some may be
      born-digital typeset editions rather than images, and one
      (`australiancouncilofhinduclergy.com/.../asthottara_sangraha.pdf`) serves
      several unrelated documents. They carry `kind: third-party` so dropping
      them is a filter, not a reparse. Doing so would take the headline 873 ->
      803. Figures re-derived 2026-09-09 from `scans.jsonl` + `scan_liveness.jsonl`;
      the earlier 55/67.9%/748 measured an older pass.
- [ ] **Rerun `check-scans` periodically.** Links rot: this pass found 114 dead
      stems of 987 stranding 338 links, and the dead ones are disproportionately
      heavily-cited anthologies. Nothing currently notices when a live link
      dies between runs.
- [ ] **`build` degrades silently when the scan files are missing.** Found
      2026-08-19 while rebuilding on a machine where `data/` held only the two
      expensive caches. `--inventory`/`--sizes`/`--listings` each hard-error
      naming the missing target; `--scans` and `--liveness` do not, so the run
      succeeds and just **omits the whole `scans` block from `tree.json`** —
      the parent project's `pdf_count` silently disappears. Worse, running
      `parse-scans` without `check-scans` restores the block at the *unfiltered*
      987 instead of the live 873, since liveness is what `build` filters on.
      Make both a hard error like the other three, or emit an explicit
      `scans: null`; a missing count must not read as "no scans".

- [ ] **Stream `check_scans` output rather than writing at the end.** A 30-min
      run currently shows nothing until it completes and loses everything if
      interrupted — it should append rows as it goes and resume from them.

## Phase 2 — independent acquisition

**The Feb-2025-vs-live diff is not being done (decided 2026-09-09).** The
snapshot earns its keep as a dating input for the changelog, not as a
comparison corpus, so the per-document "what changed in 18 months" question is
retired rather than deferred. The `Proofread by` email-stripping item went with
it: that field diffs on nearly every document only because the site stripped
addresses site-wide, and it existed solely to keep that noise out of a diff
nobody runs.

- [ ] Retire `snapshot_root()` and delete the snapshot track — `parse` /
      `parse-listings` / `recount` / `snapshot-tree`. `build` no longer depends
      on it, and with the diff retired the only remaining caller is the
      changelog's attestation, which reads `dump2020_inventory.jsonl` and
      `snapshot_inventory.jsonl` directly. Check what actually still reads the
      snapshot before deleting.

## Known gaps

- [ ] 61 documents failed to download in the original scrape
      (`dl_errors.txt` in the snapshot dir); they are absent here, not empty.
      Now answerable offline: tier 2 has fetched everything the site serves, so
      check those 61 against `data/fulltext_cache/` and against the 25 known
      404s. No requests needed.
