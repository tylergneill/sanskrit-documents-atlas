# site structure

What we have learned about sanskritdocuments.org **from the site itself** —
how its URLs behave, where its markup lies, and which of its conventions will
break a parser. Add to it; prune only what is disproven.

**Corpus figures are not here.** `make audit` measures them live and writes
them into `about.html`, which states them better and for a reader. Anything
here that could be a `data-stat` belongs there instead.

## Two axes, and they are not the same page

`Location` is the first path segment of a document's URL
(`/doc_shiva/shivaaShTakam.html` → `doc_shiva`) and the only entry in its
breadcrumb — exactly one per text. The site also publishes browsable **topic**
pages at `/sanskrit/<slug>/`, which are multi-valued.

**`Location` is a true partition** — verified three ways: no stem appears under
two folders, no `doc_id` is linked from two folder pages, and no folder page
links outside its own folder. That is what makes the folders axis safe to roll
up, and the structural opposite of the topics axis.

**A matched folder and topic page are NOT the same page.** Most folders have a
same-named topic page and it is tempting to read them as one page served twice.
None of the pairs is byte-identical, and the topic page is consistently a
**superset**. Diff them; do not assume.

The `doc_z_misc_*` folders are catch-alls — the `z_` prefix sorts them last —
and have no topic page of their own, though their texts do appear on topic
pages (`doc_z_misc_shankara` texts under `/sanskrit/shankaracharya/`).

## URL and server behavior

**A bare folder path is a rendered page, not an Apache autoindex.**
`/doc_devii/` returns 200 with a full styled page — `<meta>` description and
keywords, `itemprop` publisher/editor, favicon, `<h1>`, the document links.
None of `mod_autoindex`'s markers are present (no "Index of /", no "Parent
Directory", no `?C=N;O=D` sort links).

- **`/doc_devii/index.html` 404s**, as does any made-up filename under that
  path. There is no `index.html`; something other than "serve the file called
  index.html" answers the bare path.
- The page declares `<link rel="canonical" href="/sanskrit/doc_devii/">`, and
  `/sanskrit/doc_devii/` is byte-identical to `/sanskrit/devii/`.
- **The `Server` header varies by HTTP method** — `Apache` on HEAD,
  `nginx/1.29.8` on GET, for the same URL. It is not evidence of two backends.
  (An earlier reading of this note drew that conclusion; it was wrong.)

**The three home-page dropdowns are views, not partitions.** वर्ग (by
category), देव (by deity), and मुख्य ग्रन्थ (Major Sanskrit Works) overlap and
resolve to the same set of topic pages the sitemap lists. मुख्य ग्रन्थ is
heterogeneous — categories, individual works and authors together — and two of
its entries **leave the `/sanskrit/` namespace**: `brahmasutra` goes to
`/doc_z_misc_major_works/brahma_suutra.html`, and इतिहास points at
`/mirrors/mahabharata/` and `/mirrors/ramayana/`.

## Parse traps

**Cut `<nav>` before parsing anything.** The dropdown menu is repeated verbatim
on every page and links documents directly, so parsing a whole page files those
documents under every topic. `parse_index.strip_nav()` is the shared cut,
used by both the offline and networked halves — it stayed in this repo when
fetching moved out to rivulet, precisely because the offline parsers need it.

**The list is generated; the prose around it is not.** A folder page's document
list is machine-built — real alphabetical order by Devanāgarī title, never
leaving its own folder, never missing an entry. The trailing prose is
hand-written and carries real editorial matter. Treat the list as an index and
the prose as an essay.

**`parse_listings` takes the SLUG as the node title**, never the page's own
`<h1>` — two pages can share a heading.

## The alias trap: never merge by transliteration alone

The site's romanization is ad hoc, so two slugs that transliterate alike can be
different pages, and two that look unrelated can be the same page:

    giitaa    "other Gita" — Anugita, Uddhavagita, …   (its own page)
    gita      songs, under misc                        (a different page)

    vishhnu / vishnu / viShNu   — the same content, served under all three

`parse_listings.dedupe_aliases` detects the genuine duplicates by comparing
membership, not names. Do not add a merge rule that reasons from spelling.

## Three names per document, and only one is transliterable

| field | example | what it is |
|---|---|---|
| `title` | `Akshara Ramayanam` | the site's free-text **English label** — ad hoc romanization, no scheme, no diacritics |
| `title_deva` | `अक्षररामायणम्` | proper **Devanāgarī** |
| `doc_id` stem | `akShararAmAyaNam` | **ITRANS-flavoured, not ITRANS** |

**Only `title_deva` can be transliterated.** `title` is in no scheme — `sh`
where IAST wants `ś`, `ksh` for `kṣ`, long vowels unmarked — so feeding it to a
converter is a **silent no-op**: no Devanāgarī code points, string returned
unchanged, no error raised. That was a real bug in `docs/app.js` until
2026-08-18: every scheme rendered identically, and search could not match a
diacritic query.

**The stem is not ITRANS either**, though it resembles it. Converting a
document's Devanāgarī to real ITRANS reproduces its stem ~3% of the time. The
tells:

- **`~n` and `~N` appear in zero stems.** The site cannot write ñ or ṅ at all,
  so `पञ्च` becomes `pancha` — a systematic gap, not typos.
- **`shh` for ṣ** (`vishhnu`, `upanishhat`) where ITRANS wants `Sh`.
- **`ksh` for kṣ** where ITRANS wants `kSh`.
- `ganesha`, `raama`, `giitaa` are simply informal.

**Consequence: never feed a stem, folder, or category tag to a transliterator.**
Only `title_deva` is convertible.

**76 documents carry no `title_deva`, and they are one page template.** They
are served from the site's older template, which has no `<div id="sitename">`
banner for `parse_snapshot` to read a title from — 73 of the 76 lack it, against
399 of a 400-document control that have it. That template also loads a
different, self-hosted script stack (jQuery, `sanscript-vedic.js`,
`sanskritdocuments-transliterator-vedic.js` — "vedic" for the accent marks
Vedic recitation texts carry) where ordinary pages load the Aksharamukha plugin
from a CDN. The scripts do not cause the missing title; both are just properties
of the same template, which makes the script tag a convenient way to identify
it. An upstream gap, fixable on the site.

**The atlas fills it with a reconstruction, and that is not the same value.**
`parse_snapshot.reconstruct_deva` rebuilds a title from the `itxtitle` field,
flagged `title_deva_reconstructed`. The input is not a real transliteration
scheme (see above), so the output is lossy where every banner-read title is
exact. Neither the audit finding nor the coverage table counts a reconstruction
as the site's own: both measure the source before the repair. Getting that
wrong is what let the finding read 0 from 2026-08-28 to 2026-09-07 while all 76
were still missing upstream.

## The `inf` block's vocabulary, and its four typos

The `<pre class="inf">` block at the foot of every text is the metadata. Across
the corpus it uses **27 raw keys, naming 23 fields** — re-derive both rather than
quoting them; `parse-site` writes each run's figures to the sidecar beside the
inventory (`inf_keys` and `source_fields`).

The gap is four keys that are the site spelling an existing field differently
on a handful of documents. **They are substitutes, not duplicates**, checked
one at a time: the document with `Souce` has no `Source`, the one with `La
Jagattest update` has no `Latest update`, and the four with `Encoded and
proofread by` have no `Proofread by`. Reading past them silently loses those
documents' values — that is how one document sat with no date at all until
2026-09-07. `parse_page` folds each into its correct name, as it has always
folded `Description-comments` into `Description/comments`.

**Two keys are the site's footer, not metadata.** `Site access` is one URL on
all 9,756 documents and `Send corrections to` is one mailbox on 9,750 (in
thirteen spellings). Neither says anything about the text, so neither earns a
coverage row; the rule is written out above `COVERAGE_FIELDS` in `audit.py`.

**`Proofread by` is the input credit, and the counts are what establish it.**
The label says proofreading, but 4,389 documents name that person and nobody
else — and someone typed each of them. On an archive whose credit line exists
to thank the contributor, a document with exactly one name has that name for
the person who did the work. So the field records who input the text, not who
checked someone else's.

`Transliterated by` is a second hand where one was involved, converting into
ITRANS. It is absent from more than half the corpus, and where both names
appear (4,225 documents) they are the same person 78.7% of the time — one
contributor credited twice for one job — with the remaining fifth genuine
two-party submissions (`DSBC staff` transliterating what `Miroj Shakya`
proofread).

The four `Encoded and proofread by` documents are the corroboration, not a
counterexample: it is the only place in the corpus the site writes "encoded",
and it writes it *in the `Proofread by` slot* — one submitter, one slot, both
roles. They also carry `Transliterated by` naming the same person, so nothing
there splits encoding from proofing. Folded into `proofread_by`.

Re-derive these figures (`credit_sole`, `credit_both`, `credit_same_pct` in
`audit.credit_stats`) rather than quoting them.

**Email addresses are cut out of every credit field at parse time**
(`parse_snapshot.strip_emails`, added 2026-09-09 before this repo went public).
Upstream is mid-cleanup on this: most credit lines now carry a bare name, but
some still trail the contributor's address, and one reached `Author` — which
`build_tree.make_page` ships to every reader in `tree.json`. Publishing a
personal address that the site is itself removing is not ours to do.

Both spellings are matched: `name@host.tld` and the obfuscated `name at
host.tld` contributors write to dodge scrapers. **The cut is at the parse
boundary, not at `make_page`**, so it covers the fields that stay in
`site_inventory.jsonl` too — including `indexextra`, where an address sits
inside an HTML comment upstream clearly meant to stay unrendered.

It lowers two coverage figures, and that is correct rather than a loss: 45
`Proofread by` and 50 `Transliterated by` values were an address *and no name*,
so they empty out entirely. A field whose whole content was an email credits
nobody once the email is gone.

## The Category field is a bag

Comma-separated, in the `<pre class="inf">` block at the foot of every text. It
is **not** a controlled vocabulary and the site offers no way to browse it —
the values are plain text, not links. Some name a topic page; most name
nothing. They hold at least four different kinds of thing — source works,
people, genre terms with no page, and outright typos — and **nothing in the
field marks which kind a value is.**

## Scanned sources

Beside each document, topic and folder pages often print a parenthetical of
external links — `(Scans 1, 2, 3, Hindi 1, 2, Thesis, Kalyan 1, 2)`. These
point at archive.org items, PDFs the site hosts under `/scannedbooks/`, and
PDFs on third-party sites.

**Nothing on the page says which scan an etext was encoded from**, and the same
volume is cited by every text it contains — one Śiva-purāṇa scan sits on dozens
of stotras excerpted from it. A linked scan is *a printed witness of this text
somewhere*, not its exemplar.

**The cue vocabulary is not one axis.** The word before a link is a cue, and
hundreds of distinct ones appear, answering different questions:
`Scans`/`Scan`/`Manuscript` are about format, `Hindi`/`Bengali`/`Telugu` about
the language of *that* edition, `vyAkhyā`/`Meaning`/`Translation` about content
that is a different text. Do not treat them as one vocabulary.

**What the pipeline extracts** (`pipeline/parse_scans.py`) is deliberately
conservative: the **first parenthetical link only** — later ones are
translations, commentaries, videos and cross-references — and only where the
label is a scan-ish keyword and the target is a PDF or an archive.org item.
