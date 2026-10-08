# Audit refresh: held, not committed

Written 2026-10-08. Delete this file when the box is ticked.

`make audit-update-about` changes eleven lines of `docs/about.html` that have
nothing to do with the decimal-size pass the audit was re-run for: the
credit-field coverage counts (`cov_proofread_by` 8,569 -> 8,614,
`credit_both` 4,174 -> 4,225, `credit_same_pct` 85.7 -> 78.7, and so on) and
"pulled back to an earlier date" 153 -> 802 (42% -> 95% before mid-2020).

Two runs on 2026-10-08 gave the same new figures. The cache on this machine
was identical to a USB copy from 2026-09-07, and the published tree rebuilt
here byte-for-byte, so the published figures look stale rather than the data
-- but that is not proven until the audit runs on the machine with the
freshest cache.

- [ ] Run `make audit-update-about` on the machine with the freshest cache
      and compare. The old values mean the caches differ; the new ones mean
      commit the change as its own "audit refresh".
