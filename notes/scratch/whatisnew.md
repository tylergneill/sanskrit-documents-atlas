# whatisnew — the site's own change log

**Status (2026-11-16):** the Aug→Nov test is done (below). **Dating is built**
(v0.2.0, `parse_whatisnew` + `build_changelog --attest-events`, figures on the
About page). **The monthly partial refresh is designed but not built**: it waits
on a decision about refetch semantics, i.e. overwriting a cached page and
keeping the previous copy. Keep a full fetch every 6–12 months.

Pointed out by the site admin. `https://sanskritdocuments.org/whatisnew` is a
dated event log of additions and updates. If it reliably names what changed,
a refresh could fetch only those documents instead of all ~9900, and the
About page's collection history gets a source that is an actual event record,
unlike `Latest update`, which keeps only the most recent touch.

## What the page is (measured from one fetch, 2026-11-16)

- One `<LI>` per event, after `</nav>` (cut it with `parse_index.strip_nav`,
  since the nav also holds `<LI>`s):

      Files <stem>.* (added|updated) <a href='/<location>/<stem>.html'> title </a> on YYYY-MM-DD

  All 630 body items matched that shape, all dates ISO. The href gives the
  `doc_id` directly.
- **The current page covers 2026 only**: 2026-01-07 → 2026-11-04, 630 events
  over 597 documents, 467 `added` / 163 `updated`. Since 2026-08-15: 226
  events (167 added, 59 updated).
- Earlier years are separate pages linked from the footer:
  `whatisnew_2025.php`, `_2024.php`, `_2023.php`, `_2021-2022.php`,
  `_2020back.php` ("updates in 2020 and before"). The header claims coverage
  "since April 2010". Fetched 2026-11-16 into the session scratchpad; a
  pipeline step should cache them under `data/metadata_cache/`.
- The 2020 snapshot holds its own copy at
  `2020-sanskrit-documents-dump/sanskritdocuments.org/whatisnew/index.html`.
  That's an offline cross-check on whether old entries were later rewritten.
- The site's footer now says automated scraping and bulk downloading need
  prior written permission. The Cloudflare exception was granted for our
  User-Agent; it's worth having that permission in writing, and keeping it
  recorded somewhere, before anything ships that depends on refetching.

## Preliminary findings (2026-11-16, all six pages + the 2020 snapshot's copy)

Scripts kept in the session scratchpad only; re-derive rather than cite.

- **Size.** 12,792 distinct events (after removing duplicates across the
  overlapping pages) naming 9,789 doc_ids, 2010-04-25 → 2026-11-04. 17 of
  ~13.3k entries failed to parse, all with a stray space in the href
  (`/doc_ deities_misc/`). Easy to fix.
- **Three formats.** ISO dates with the doc in the href (most entries); and,
  2010–2017, `Files X.* are added in folder <a>doc_…</a> on Oct 3 2010` or
  `… on 29 Jul 2016`.
- **Append-only, apart from pruning.** Against the 2020 snapshot's copy
  (5,975 entries for the same span), today's pages add nothing and drop 54
  (<1%). No surviving entry's date has been changed. The 54:
  - **33 entries / ~19 docs since deleted from the site**: Shirdi and Satya
    Sai texts, the Tyagabrahma sahasrakam, two Bhuvaneshvari 108-name texts,
    the `doc_z_otherlang_maraathii` folder, `dhanvantaristotra3`. **Deleting
    a document deletes its log history.**
  - **Renames and moves lose the birth date.** `shivastutiHdaksha` moved
    `doc_ganesha` → `doc_shiva`: its 2020-04-25 `added` is gone, and the new
    path shows only a 2026-08-26 `updated`.
    `shivasahasranAmastotradevIbhAgavata` (added 2018) reappears in November
    as `…mahAbhAgavata` with a single 2026-07-29 `updated`; this is one of the
    3 Aug→Nov catalogue removals.
  - **15 older `updated` lines pruned from docs that are still listed**
    (`vsahasranew` lost five from 2014–2020, `raatrisuukta2` four, and
    `saarthaatharva` three). Usually an `added` line or a later `updated`
    survives. It looks like occasional hand-tidying of repeat updates, not a
    rule.
  - **So a document's first logged event is an upper bound on its birth**:
    "existed by then". That's the same kind of evidence as the 2020
    snapshot, so the two combine by taking the earlier date.
- **Coverage.** 9,346 of 9,957 November-catalogue docs (93.9%) have at least
  one event, 8,250 an `added` one. 438 logged doc_ids match nothing in today's
  catalogue: renamed, removed, or typo'd upstream.
- **Consistent with the 2020 snapshot.** 3,058 of 3,068 docs logged as added
  on or before 2020-06-27 are in it, and only 4 of 5,182 later
  additions were already there. The log's add dates hold up against
  independent evidence.
- **It disagrees with `Latest update` in both directions.** That's the
  measure the changelog stands on. Compared on the August inventory:
  - 7,230 same month.
  - 1,550 have a logged event later than their stamp (e.g. `varbrhs` stamped
    1992, updated 2025-05-24 in the log), so the stamp is not reliably a
    "last touch".
  - 365 have a stamp later than any logged event: edits that were never
    logged.
  - 602 have no event before August.
- **It gives birth dates the atlas lacks.** For 1,042 docs the first event is
  earlier than `Latest update`. That is the gap `growth-from-last-updated.md`
  describes: a text reproofed in 2023 currently appears only under 2023.
- **Gaps.** 2011–2016 are thin; 2015 logs 1 addition against 296 updates.
  2010 carries a batch logged when the log began. 797 docs have pre-2010
  stamps the log can only place as "by April 2010". So the log can't replace
  the stamps; it complements them, with the 2020 snapshot as a third input.
- **Forward test, additions half (catalogues only).** August→November the
  catalogue gained 179 docs:
  - 162 have an `added` event after 2026-08-11.
  - 16 were logged as added 07-29 → 08-08, *before* the August walk, yet
    weren't linked from any listing on 08-11. The log runs ahead of the
    listings.
  - A refresh window keyed off the log therefore needs a margin before the
    last walk; a few weeks covered every case here.
  - The 3 docs removed from the catalogue have no log trace. There's no
    `removed` verb.
- **Forward test, changed half (full cache, 9,754 docs in both).** Bodies
  compared after decoding Cloudflare emails (see below):
  - 310 bodies changed. The log names 52 of them (**recall 17%**), and every
    one of the 52 really changed (**precision 100%**).
  - Of the 258 unlogged:
    - 70 are pure batch edits to credit lines (one contributor's
      "Dr. … Kendrapara, Orisa" → "Prof. … Puri, Odisha" on ~60 docs, plus
      addresses removed).
    - 66 carry a corpus-wide spelling sweep (सिध्य → सिद्ध्य); 28 have
      nothing else changed.
    - The rest are individual proofreading edits, mostly under 400
      characters. A few large restructurings (`yudhiShThiragiitaa` −15.7k
      characters, `upadeshasAram`, `brahmavidya`) went unlogged too.
  - Metadata the atlas renders, unlogged: 35 documents changed categories
    (normalized, compared as sets; mostly purana/veda source tags added),
    ~17 titles, 15 `Latest update` stamps.
- **Two site-wide served-HTML changes since August**, both normalized at parse
  time now:
  - Cloudflare email obfuscation, on 1,100+ pages
    (`parse_index.decode_cf_emails`; rivulet's text extractor has a twin).
  - Absolute download hrefs, on ~3,000 pages (`parse_snapshot.parse_links`).

  Without the normalizing, each looks like thousands of edited documents.

## Refresh strategy this points to

Monthly incremental pass, full fetch every 6–12 months:

1. Tier-1 walk (~108 requests) plus the current `whatisnew` page (1 request).
   Diffing the catalogue catches additions, removals and renames without the
   log. The log can't see removals and drops a renamed document's history.
2. Fetch:
   - documents new to the catalogue;
   - documents logged since the last pass, with a ~3-week overlap (the log
     ran up to 13 days ahead of the listings in August);
   - logged documents not yet in the catalogue, kept as pending.

   At 2026's rate (~60 events/month) that's roughly 100–200 requests a
   month, against ~9,900 for a full fetch.

What it misses between full fetches, per quarter (Aug→Nov, full cache): ~258
text edits, mostly small or batch, plus 35 category changes, ~17 titles and 15
`Latest update` stamps. That's tolerable for 6 months. A rotating twelfth of
the corpus each month (~800 requests) is the alternative to a yearly 5-hour
burst: the same yearly total, nothing older than a year.

## How the test was run

The test compared the two caches (the August one has since been deleted),
`data/archive-2026-08/fulltext_cache/` and
`data/fulltext_cache/`. For each document, the prediction is any log event dated
on or after that document's own August `fetched_at`, minus a day. Bodies are
compared by `id="content"` block only, since the page boilerplate (nav,
analytics, Cloudflare beacon) changes on its own.

## Not yet

- About page credits for Sunder Hattangadi and Nandu Abhyankar at the very
  top. **On hold until Nandu confirms the wording.** Do not add them
  before then.
