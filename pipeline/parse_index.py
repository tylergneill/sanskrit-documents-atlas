"""Parsing the site's index pages -- the offline half of the old fetch_metadata.

**These functions touch no network.** They take a page that is already on disk
and pick the structure out of it, which is why they stayed public when the
fetching moved to `rivulet`: `parse_scans` and `parse_listings` read the cached
index without obtaining anything, and must keep working on a checkout that has
no rivulet installed.

The networked half -- the sitemap walk that writes `metadata_cache/` and
`catalogue.jsonl` -- now lives in
`rivulet/extract/sanskrit_documents/fetch_metadata.py`, which imports the
parsing from here. That is the allowed direction: rivulet may depend on an
Atlas, an Atlas may never require rivulet.

`SITE_BASE` and `USER_AGENT` live here rather than beside the fetcher because
both halves need them -- `subpage_links` builds absolute URLs from the former,
and the latter identifies this project to the site in every request any part of
it makes.
"""

import re

SITE_BASE = "https://sanskritdocuments.org"
SITEMAP_URL = f"{SITE_BASE}/sitemap/"

USER_AGENT = (
    "sanskrit-documents-atlas/0.1 (+https://github.com/tylergneill/"
    "sanskrit-documents-atlas; tyler.g.neill@gmail.com) "
    "reading the public category index to build a browsable atlas"
)

HREF_RE = re.compile(r'<a[^>]+href="([^"]+)"', re.IGNORECASE)

# Every listing repeats the site's dropdown menu inside <nav>, and that menu
# links documents directly (`/doc_z_misc_major_works/brahma_suutra.html` is in
# all 87). Those links are navigation, not membership.
NAV_RE = re.compile(r"<nav\b.*?</nav>", re.IGNORECASE | re.DOTALL)


def strip_nav(page: str) -> str:
    """Drop the repeated site navigation, leaving the listing's own content."""
    return NAV_RE.sub("", page)


def subpage_links(page: str) -> dict[str, str]:
    """Sitemap -> {slug: url} for every `sanskrit/<topic>/` listing."""
    links = {}
    for href in HREF_RE.findall(page):
        clean = href.lstrip("/")
        if clean.startswith("sanskrit/"):
            slug = clean.replace("/", "_").strip("_")
            links[slug] = f"{SITE_BASE}/{clean}"
    return links


def docpage_links(page: str) -> list[str]:
    """A listing -> the `/doc_*/*.html` documents it points at.

    The `Z`->`z` replacement and the `otherlang` exclusion are carried over
    verbatim from the original scrape; without them the live set and the
    snapshot's would differ for reasons that are ours, not the site's.
    """
    found = []
    for href in HREF_RE.findall(page):
        if not href.startswith("/doc_"):
            continue
        if not href.split("?")[0].endswith(".html"):
            continue
        if "otherlang" in href:
            continue
        found.append(href.replace("Z", "z"))
    return found


def doc_id_of(href: str) -> str:
    """`/doc_shiva/foo.html` -> `doc_shiva/foo`."""
    return href.lstrip("/").removesuffix(".html")
