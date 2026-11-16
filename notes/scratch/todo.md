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
- [ ] **Rerun `check-scans` periodically.** Last run 2026-11-16, over all
      1,012 stems: 887 live. Since 2026-08-18, 24 went dead, 6 came back, and
      all 27 new stems are live. 14 timeouts were retried once and 6 of those
      came back, so a single pass undercounts. A retry-on-timeout inside
      `check_scans` would beat the hand retry done this time. Links rot: the August pass found 114 dead
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

- [x] **Test whether `whatisnew` predicts what changed Aug → Nov 2026.** Done
      2026-11-16: precision 100%, recall 17% of text changes. Most misses are
      batch or small edits. See `whatisnew.md`.
- [ ] **Monthly partial refresh (stage 2 of `whatisnew`). Due ~2026-12-16,** a
      month after the 2026-11-16 full fetch. Instead of refetching all ~9,950
      pages, refetch the few hundred that the catalogue diff and the change log
      say are new or changed: ~110 index requests plus ~100–200 documents,
      against ~9,950. Keep a full fetch every 6–12 months; the next one is due
      by 2027-05. Evidence and figures are in `whatisnew.md` ("Refresh
      strategy").

      **Decide first (Tyler):**
      - *Refetch semantics.* Today a file in `fulltext_cache/` means "done",
        so nothing is ever refetched. A refresh must overwrite deliberately.
        Proposal: before overwriting, move the old page to
        `data/fulltext_previous/<location>/<stem>.<fetched-date>.html`,
        following EBS's `fulltext_previous/`, so every refresh stays diffable
        and nothing is lost to a bad fetch.
      - *Removals.* A document dropped from the catalogue: leave it in the
        cache, but out of `build` (the catalogue already gates that), or move
        it to `fulltext_previous/`? Proposal: move it, so the cache equals
        the catalogue again.
      - *Control sample.* Also refetch a random ~100 documents the log did not
        name, to measure each month what the log misses, instead of relying on
        the one Aug→Nov measurement. Costs ~100 requests. Proposal: yes,
        until a few months agree.

      **Build:**
      1. Atlas, offline: `pipeline/plan_refresh.py` → `data/refresh_plan.jsonl`.
         Inputs: the new and previous `catalogue.jsonl`, `whatisnew_events.jsonl`,
         and a small state file recording the last pass date
         (`data/refresh_state.json`, written only when a refresh completes).
         Rows: `{doc_id, reason}`, where `reason` is one of `new` (in
         catalogue, not cached), `logged` (an event since last pass minus 21
         days), `pending` (logged, not yet in any listing; carried forward,
         not fetched), `removed`, or `control`. Case-insensitive log matching
         as in `build_changelog.load_event_attestations`.
      2. rivulet: `fetch_fulltext --refetch data/refresh_plan.jsonl`. Same
         terms and same block-stop rule; journals with `"refetch": reason`;
         moves the old copy aside per the decision above; skips `pending`.
         Keep `--refetch` out of the default walk so `make fetch-text`
         behaves exactly as now.
      3. Makefile: `plan-refresh`, `fetch-refresh`. One `make refresh`
         that chains `fetch-metadata` → `fetch-whatisnew --main-only` →
         `parse-whatisnew` → `plan-refresh` → `fetch-refresh`, then stops
         before the offline rebuild so the plan can be read first.
      4. A tiny report in `plan_refresh`: counts per reason, plus the
         `control` sample's hit rate after the fetch (how many unlogged
         documents had actually changed). Append that rate to
         `whatisnew.md`, so the full-fetch interval gets decided from
         measurements.

      **Run (next month):** first `make refresh`, then read the plan and
      the report. Then the usual rebuild: `parse-site parse-listings-site
      count-sizes extract-text build changelog audit-update-about`, then
      `make data` in sagara-sangama. Before the first run, copy
      `data/fulltext_cache/` to Gaston, as the pre-refresh baseline.

      **Watch for:** the log running ahead of the listings (13 days in
      August), which is why the overlap is 21 days. Renames show up as one
      removal plus one addition, and the renamed document loses its log
      history, so its start date can regress. Check
      `log_pulled_back` doesn't drop unexpectedly. Also served-HTML changes
      like November's Cloudflare front: if many unlogged control documents
      "change", diff one before believing it.
- [ ] **42 documents are linked from listings only as cross-references**, as
      absolute `https://sanskritdocuments.org/doc_…` links inside another
      entry's "(stotram, nAmAvalI)" parenthetical, so they're in no catalogue.
      Most look like broken links upstream (wrong folder, typos, `_indexed`
      and `trial/` paths). A few appear in the log or the 2020 snapshot
      (`paaravatisahasra`, `sItAsahasranAmastotramadbhutarAmAyaNa`,
      `tripurasundarIshatanAmastotram`). Worth ~42 requests to see which
      resolve, then maybe a report to the site. Taking them as membership was
      tried and reverted; see `parse_index.docpage_links`.
- [x] **`whatisnew` as a dating source.** Done 2026-11-16 (v0.2.0):
      `fetch-whatisnew` / `parse-whatisnew`, `build_changelog
      --attest-events`. The About page publishes the figures. The chart
      pulls back 1520 documents, up from 820.
- [ ] **An additions-per-month view from `whatisnew`**, as distinct from the
      last-touch chart: the log's `added` events are a real arrival series
      from 2010, with gaps in 2011–2016. Not built. Would need the frontend
      to plot a second series.
- [ ] **About page credits** for Sunder Hattangadi and Nandu Abhyankar. On
      hold until Nandu confirms.
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
