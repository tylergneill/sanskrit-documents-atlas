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


# The site went behind Cloudflare between the 2026-08 and 2026-11 fetches, and
# Cloudflare's email obfuscation rewrites every plain address in a served page
# into a placeholder that carries it XOR-encoded:
#
#     <a href="/cdn-cgi/l/email-protection" class="__cf_email__"
#        data-cfemail="<hex>">[email&#160;protected]</a>
#
# (and a `<span>` form, 3 pages). Left alone, it makes ~1100 untouched
# documents look edited, inflates their byte counts, and slips past
# `parse_snapshot.strip_emails`, which looks for `@`. Decoding restores the
# page to what the site's files contain, so the rest of the pipeline sees what
# it always saw, and the existing email stripping applies to credit fields as
# before. The cache stays exactly as served; this runs at read time.
#
# rivulet's `extract/sanskrit_documents/text_extractor.py` restates this
# decoder, because it runs and is tested without this repo on the path. Change
# both together. They were checked equal on all 1,112 obfuscated pages of the
# 2026-11 cache.
CF_EMAIL_RE = re.compile(
    r'<(a|span)\b[^>]*\bdata-cfemail="([0-9a-fA-F]+)"[^>]*>.*?</\1>',
    re.IGNORECASE | re.DOTALL,
)


def _cf_decode(hexstr: str) -> str:
    """The first byte is the XOR key for the rest."""
    data = bytes.fromhex(hexstr)
    return bytes(b ^ data[0] for b in data[1:]).decode("utf-8", "replace")


def decode_cf_emails(page: str) -> str:
    """Undo Cloudflare's email obfuscation in a served page; no-op without it."""
    if "data-cfemail" not in page:
        return page
    return CF_EMAIL_RE.sub(lambda m: _cf_decode(m.group(2)), page)


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
        # Relative hrefs only, deliberately. A listing's absolute document
        # links (`https://sanskritdocuments.org/doc_…`, ~2400 in 2026-11) are
        # cross-references inside another document's entry -- a nAmAvalI's
        # "(stotram, nAmAvalI)" pointer to its companion -- not membership.
        # Accepting them was tried 2026-11-16: 567 documents gained topics
        # they are not on, and 42 cross-reference targets that no listing
        # includes (many wrong-folder or typo links) entered the catalogue.
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
