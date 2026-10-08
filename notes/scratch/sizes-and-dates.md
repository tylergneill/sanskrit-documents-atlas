# Sizes and dates

Part of a pass across all seven repos, coordinated in
`sagara-sangama/notes/scratch/sizes-and-dates.md` -- read that first for what
was decided and why. This file lists only what is left **here**. Delete it
when the boxes are ticked. Written 2026-10-08.

Branch: `fix-sizes-and-dates`.

## Done here

- Sizes are decimal everywhere (1 MB = 1,000,000 bytes).
- `__content_version__` is already the newest fetch in the journal.
- The print-source badge on the tree page reads "PDF", not "scan".

## Left here

- [ ] **Publish `all_stats.sourced`** in `docs/data/tree.json`: the date this
      Atlas took its copy of the collection, YYYY-MM-DD. It must be the same
      value `__content_version__` gets in `docs/VERSION`, written in the same
      place, so the two cannot disagree. `stamp_version` in
      `pipeline/build_tree.py` computes it; `all_stats` is `root["stats"]`
      in the same file.
- [ ] Rebuild the tree; commit `tree.json` and `docs/VERSION` together.
- [ ] **Re-run the audit on the machine with the freshest cache** and compare.
      The two size figures in the About prose (132.6 MB, 2.8 KB) were set by
      hand and confirmed by an audit run on 2026-10-08. That run also changed
      eleven unrelated lines (credit-field coverage; "pulled back to an
      earlier date" 153 -> 802), which were **not** committed. See section 4
      of the central note before committing them.
