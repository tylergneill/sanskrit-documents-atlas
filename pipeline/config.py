"""Where the pipeline reads from and writes to.

**The older corpora live together under one root**, a sibling of the atlases
inside `sagara-sangama` (moved there 2026-08-20, restructured the same day):

    third_party_dumps/sanskrit-documents/
        2025-my-own-dump/
            docpage_html_dls/    8547 document pages   -- the Feb-2025 snapshot
            subpage_html_dls/    87 listing pages
        2020-sanskrit-documents-dump/
            sanskritdocuments.org/   the 2020-06-27 `wget -r` mirror

Both are read-only: nothing here writes to them. The defaults below derive from
`_DUMPS_ROOT` so the layout is stated once; override the root with SDA_DUMPS,
or either corpus individually with SDA_SNAPSHOT / SDA_DUMP_2020 (or --snapshot
/ --dump on the stages that read them). Paths resolve relative to this file,
never the working directory, so stages behave the same wherever they're invoked
from.

**Both are the author's own**, despite the `third_party_dumps/` parent (the 2020
mirror genuinely is someone else's; the directory is named for the general
case). The Feb-2025 scrape is an earlier, less mature pass by the same person --
**not third-party**. It is a cross-check because of its age and method, not its
provenance.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# sagara-sangama/third_party_dumps/sanskrit-documents -- four levels up from
# this file (pipeline/ -> atlas -> atlases/ -> sagara-sangama/).
_DUMPS_ROOT = Path(
    os.environ.get("SDA_DUMPS")
    or REPO_ROOT.parent.parent / "third_party_dumps" / "sanskrit-documents"
).expanduser()

_DEFAULT_SNAPSHOT = _DUMPS_ROOT / "2025-my-own-dump"

DATA_DIR = REPO_ROOT / "data"
DOCS_DATA_DIR = REPO_ROOT / "docs" / "data"

# Snapshot-derived, and named so: these describe the Feb-2025 scrape, not the
# live site. A later independent pull writes alongside them, and the prefix
# keeps which-came-from-where legible once both exist.
INVENTORY_PATH = DATA_DIR / "snapshot_inventory.jsonl"
SIZES_PATH = DATA_DIR / "snapshot_sizes.jsonl"
# The 87 listing pages, parsed into membership: which documents each one links.
# Snapshot-derived like the two above -- the same pages `fetch-metadata`
# re-fetches live, but read off disk, so this stage costs no requests.
LISTINGS_PATH = DATA_DIR / "snapshot_listings.jsonl"

# SITE-DERIVED twins of the two snapshot stages above, parsed from
# `fulltext_cache/` -- our own 2026-08 fetch rather than the Feb-2025
# Feb-2025 scrape. Same parsers, different corpus: the page format did not
# change, so `parse_snapshot` and `recount_sizes` take a `--docroot` and write
# here instead. These are what `build` reads; the snapshot pair feeds
# `snapshot-tree`, and the two are never combined.
SITE_INVENTORY_PATH = DATA_DIR / "site_inventory.jsonl"
SITE_SIZES_PATH = DATA_DIR / "site_sizes.jsonl"
SITE_LISTINGS_PATH = DATA_DIR / "site_listings.jsonl"
# Scanned source PDFs, harvested from the same listing and location pages.
# These are NOT the per-script PDFs the site generates from its own encoded
# text (those are a suffix on the doc_id and are handled in parse_snapshot);
# these are photographed originals under /scannedbooks/, linked in prose
# alongside archive.org references. Same pages, different fact, so a separate
# stage and a separate file.
SCANS_PATH = DATA_DIR / "scans.jsonl"
# Everything the scan rule dropped, with a `reason`. Kept because the
# rule is deliberately conservative: the rejects are where the next
# refinement comes from, notably PDFs labelled with a book title
# instead of a keyword.
SCANS_REJECTED_PATH = DATA_DIR / "scans_rejected.jsonl"
# Whether each distinct scan stem still resolves. One row per stem, not per
# link -- `make check-scans`, networked but not against sanskritdocuments.org.
SCAN_LIVENESS_PATH = DATA_DIR / "scan_liveness.jsonl"

# Site-derived, in two tiers that mirror how the site is shaped.
#
# TIER 1 -- metadata: the sitemap's ~20 location pages and the 87 category
# listings. Cheap (~88 requests), and the ONLY thing that says what documents
# exist, so it is what the full scrape list is built from.
#
# Two subdirectories because they are two different kinds of page that happen
# to be fetched together: `locations/` holds the sitemap's `sanskrit/<topic>/`
# pages, `listings/` the `/doc_*/` category pages they link to. Keeping them
# apart means a reparse can tell which tier a cached file came from without
# re-deriving it from the URL.
METADATA_CACHE_DIR = DATA_DIR / "metadata_cache"
LOCATION_CACHE_DIR = METADATA_CACHE_DIR / "locations"
LISTING_CACHE_DIR = METADATA_CACHE_DIR / "listings"
METADATA_LOG_PATH = DATA_DIR / "metadata_fetch_log.jsonl"
CATALOGUE_PATH = DATA_DIR / "catalogue.jsonl"

# TIER 2 -- the documents themselves, one raw docpage per text, laid out as
# `<location>/<stem>.html` to mirror the snapshot. Raw HTML rather than
# extracted text: the page carries the body AND its `% Field : value` block, so
# keeping it whole means a reparse costs local work instead of 8547 requests.
FULLTEXT_CACHE_DIR = DATA_DIR / "fulltext_cache"
TEXT_LOG_PATH = DATA_DIR / "text_fetch_log.jsonl"

# The datestamp the frontend shows. `__content_version__` is DERIVED from
# text_fetch_log.jsonl at build time rather than hand-maintained -- it read
# 2025-02-16 for months because nobody edits a file nothing writes to.
VERSION_PATH = REPO_ROOT / "docs" / "VERSION"

TREE_PATH = DOCS_DATA_DIR / "tree.json"
# The snapshot track's own output. Same shape as tree.json so the frontend
# can read either; which one it gets is a serve-time choice, never a
# build-time one. They are alternatives and are never combined.
SNAPSHOT_TREE_PATH = DOCS_DATA_DIR / "snapshot_tree.json"

# The thirty-year growth curve, bucketed by each document's own `Latest
# update`. Two tracks like the tree above, and for the same reason: the
# snapshot's is 8547 documents ending in Feb 2025, ours is 9756 ending
# whenever the fetch ran. Only the real one is published.
CHANGELOG_PATH = DOCS_DATA_DIR / "changelog.json"
SNAPSHOT_CHANGELOG_PATH = DOCS_DATA_DIR / "snapshot_changelog.json"

SUBPAGE_DIRNAME = "subpage_html_dls"
DOCPAGE_DIRNAME = "docpage_html_dls"


def snapshot_root(override: str | None = None) -> Path:
    """Resolve the snapshot directory, preferring an explicit override."""
    raw = override or os.environ.get("SDA_SNAPSHOT")
    path = Path(raw).expanduser() if raw else _DEFAULT_SNAPSHOT
    return path.resolve()


# A THIRD observation of the corpus, older than either build track: a 2020
# `wget -r` mirror of the whole site, kept as a git repo outside this one.
# Unlike the Feb-2025 snapshot it is not a build input -- no tree is built from
# it. It serves one purpose: dating. A document it holds existed by
# DUMP_2020_DATE whatever its `Latest update` claims today, which is what
# `build_changelog --attest` uses to pull revised documents back toward their
# real arrival year.
#
# Its document pages sit under `doc_<location>/` at the mirror root rather than
# in a `docpage_html_dls/` sibling, so `dump_docroot()` builds the view
# `parse_snapshot --docroot` expects. Keep the `doc_` prefix on the link names:
# `doc_id` is `<location>/<stem>` and both other corpora carry the prefix in
# `location`, so stripping it silently zeroes every join against them.
DUMP_2020_DATE = "2020-06-27"

_DEFAULT_DUMP_2020 = (
    _DUMPS_ROOT / "2020-sanskrit-documents-dump" / "sanskritdocuments.org"
)

DUMP_2020_INVENTORY_PATH = DATA_DIR / "dump2020_inventory.jsonl"

# When the Feb-2025 scrape was taken. It attests existence like the 2020 mirror
# does, just later: a document in it was live by this date whatever its own
# `Latest update` claims. Named here because the Makefile's `ATTEST` and
# `audit.intro_stats` both need it, and a date that disagrees between them
# would publish a figure the chart does not support.
SNAPSHOT_DATE = "2025-02-16"


def dump_2020_root(override: str | None = None) -> Path:
    """Resolve the 2020 mirror, preferring an explicit override."""
    raw = override or os.environ.get("SDA_DUMP_2020")
    path = Path(raw).expanduser() if raw else _DEFAULT_DUMP_2020
    return path.resolve()
