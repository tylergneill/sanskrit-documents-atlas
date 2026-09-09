"""Stage 2b: OUR OWN fetch -> docs/data/tree.json.

Reads `site_inventory.jsonl` + `site_sizes.jsonl`, both parsed from
`data/fulltext_cache/` -- the 9756 documents of the 2026-08-11..15 tier-2
fetch. **This is the real build track.** The earlier Feb-2025 scrape has
its own builder (`build_snapshot_tree.py` -> `snapshot_tree.json`) and the two
are never combined; which one the frontend gets is a serve-time choice.

Until 2026-08-18 this module read the SNAPSHOT's inventory and sizes, so the
published atlas was 18 months stale while its datestamp quietly said so and
nothing else did.

Emits the node schema the sanskrit-wikisource-atlas frontend consumes, so
docs/app.js works essentially unchanged.

Unlike the sibling atlases, this corpus has no single hierarchy. The site files
each document in exactly one `Location` (its directory: doc_shiva, doc_veda,
...) but *also* lists it on curated topic pages, averaging 2.24 of those. Both
are real navigational axes, so both are emitted as sibling branches of the root:

    by folder -- the canonical placement, one document in exactly one node
    by topic  -- the site's own 87 topic pages, a document on each that lists it

Only "by folder" is counted in `all_stats`; the topic branch re-reaches
the same documents and would double-count. Each branch's own nodes carry
distinct-document stats (`distinct_stats`), which is what the sidebar shows.

**The `Category` facet is deliberately not a branch.** It was one until
2026-08-13, and it was the wrong shape for the data: the field is uncontrolled
free text mixing genres with author names and typos, and rendering it as a
hierarchy of ~300 peers implied a taxonomy that does not exist. It is now a
*filter* in the frontend, driven by each page's `meta.categories` -- a filter
has no rollup, so it cannot reproduce the placement double-count that branch
shipped with. Tags arrive here already normalized by `pipeline/parse_snapshot`;
this stage does not fold them.

This stage never reads the snapshot, so it is fast (~1s).

Run: python -m pipeline.build_tree
"""

import argparse
import datetime
import json
from pathlib import Path

from pipeline.build_changelog import corpus_date, parse_update
from pipeline.config import (SCAN_LIVENESS_PATH, SCANS_PATH,
                             SITE_LISTINGS_PATH,
                             SITE_INVENTORY_PATH, SITE_SIZES_PATH,
                             TEXT_LOG_PATH, TREE_PATH, VERSION_PATH)

STAT_KEYS = ("raw_bytes", "content_bytes", "transliterated_bytes")

# The 20 docpage directories are machine names; these are the site's own labels
# for them, taken from its navigation.
LOCATION_LABELS = {
    "doc_deities_misc": "anya devatā",
    "doc_devii": "devī",
    "doc_ganesha": "gaṇeśa",
    "doc_giitaa": "gītā",
    "doc_hanumaana": "hanumān",
    "doc_purana": "purāṇa",
    "doc_raama": "rāma",
    "doc_shiva": "śiva",
    "doc_subrahmanya": "subrahmaṇya",
    "doc_upanishhat": "upaniṣad",
    "doc_veda": "veda",
    "doc_vishhnu": "viṣṇu",
    "doc_yoga": "yoga",
    "doc_z_misc_general": "misc: general",
    "doc_z_misc_major_works": "misc: major works",
    "doc_z_misc_misc": "misc: misc",
    "doc_z_misc_navagraha": "misc: navagraha",
    "doc_z_misc_shankara": "misc: śaṅkara",
    "doc_z_misc_sociology_astrology": "misc: sociology & astrology",
    "doc_z_misc_subhaashita": "misc: subhāṣita",
}


# doc_ids whose extracted text is on THIS machine, or None if unknowable.
# Module-level rather than threaded through make_page: it is a fact about the
# local filesystem, not about the corpus.
_HAS_TEXT: set[str] | None = None

# Where rivulet writes the cleaned plain text. Read, never written, here.
TEXT_EXTRACT_DIR = Path("data/text_extract")


def load_has_text(base: Path = TEXT_EXTRACT_DIR) -> set[str] | None:
    """doc_ids with an extracted .txt on disk, or None if there is no extract.

    Walks the tree rather than trusting the catalogue: it lists 30039
    documents while only ~9.7k pages have ever been fetched, so presence on
    disk is the only honest answer to "is there text for this".
    """
    if not base.is_dir():
        return None
    return {str(p.relative_to(base).with_suffix("")) for p in base.rglob("*.txt")}


def load_sizes(path: Path) -> dict[str, dict]:
    sizes = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            sizes[record["doc_id"]] = {k: record[k] for k in STAT_KEYS}
    return sizes


def empty_stats() -> dict:
    return {**{k: 0 for k in STAT_KEYS}, "count": 0, "text_count": 0}


def accumulate(target: dict, source: dict) -> None:
    for key in STAT_KEYS:
        target[key] += source.get(key, 0)
    target["count"] += source.get("count", 0)
    target["text_count"] += source.get("text_count", 0)


def make_node(node_id: str, title: str, node_type: str = "category") -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "title": title,
        "children": [],
        "pages": [],
        "index_items": [],
        "stats": empty_stats(),
    }


def compact_downloads(record: dict) -> list[str]:
    """Download links as bare script tags.

    Every href is `/<doc_id><suffix>.<ext>` -- the same path repeated per
    format, which cost 3.3 MB of tree.json in full. Only the varying part is
    kept ("ITX", "Tamil PDF", ...); the frontend rebuilds the URL from doc_id.
    """
    labels = []
    for label, href in record["downloads"].items():
        if href.startswith("javascript:"):
            continue
        labels.append(label)
    return labels


def compact_scans(rows: list[dict]) -> list[dict]:
    """Scan links for one document, as {u: url, k: kind}.

    Short keys and no label: at ~5000 documents every byte of key name is 5 KB
    of tree.json, and the label ("Scan", "Scans", "Text") is a site-side
    formatting artifact that tells a reader nothing the icon does not. `kind`
    stays because it is the one thing a reader might act on -- whether the
    target is archive.org, the site's own `/scannedbooks/`, or a third-party
    host of unverified nature.

    The URL is stored in full. Unlike the download hrefs, it is derivable from
    nothing: archive.org item names are opaque and the page anchor varies per
    document.
    """
    return [{"u": row["url"], "k": row["kind"]} for row in rows]


def make_page(record: dict, sizes: dict[str, dict], suffix: str = "",
              scans: dict[str, list[dict]] | None = None,
              ceiling: "datetime.datetime | None" = None) -> dict:
    measured = sizes.get(record["doc_id"], {k: 0 for k in STAT_KEYS})
    has_text = measured["content_bytes"] > 0
    stats = {**measured, "count": 1, "text_count": 1 if has_text else 0}

    # Titles repeat across the corpus, so the node id keys on doc_id. The
    # suffix distinguishes the same document's node in the category branch.
    # url is omitted: it is `https://sanskritdocuments.org/<doc_id>.html` for
    # every document, and spelling it out cost 0.6 MB. The frontend derives it,
    # as it does the download hrefs.
    page = {
        "id": f"doc:{record['doc_id']}{suffix}",
        "type": "page",
        "title": record["title"] or record["stem"],
        # Set only when this build could see extracted text on disk for this
        # document; see load_has_text. Lets a local `--fulltext` server offer a
        # link, and lets Sagarasangama render one, without either reading
        # data/ directly. Omitted (not False) when there is no extract at all
        # -- "could not tell" and "no text" are different claims.
        **({"has_text": True}
           if _HAS_TEXT is not None and record["doc_id"] in _HAS_TEXT
           else {}),
        "stats": stats,
        "own_stats": dict(stats),
        "subpages": [],
        "meta": {
            "doc_id": record["doc_id"],
            "title_deva": record["title_deva"],
            "categories": record["categories"],
            "downloads": compact_downloads(record),
        },
    }
    # Only what the frontend reads. `language`, `subject`, `texttype`,
    # `proofread_by`, `transliterated_by` and `description` were shipped here
    # until 2026-09-07 and no code path ever read them -- 1.6 MB, 14% of the
    # file, parsed by every visitor to be ignored. They stay in
    # `site_inventory.jsonl`, which is what the audit's coverage table counts,
    # so dropping them costs the atlas no knowledge; it only stops mailing it
    # to readers who cannot see it.
    #
    # Restoring one is a line here plus the code that renders it, in the same
    # change -- that pairing is the whole discipline. `subject` is the one to
    # leave out regardless: 92% of documents carry the single value
    # `philosophy/hinduism/religion`, so it separates nothing.
    if record.get("author"):
        page["meta"]["author"] = record["author"]
    # `Latest update` normalized to `YYYY-MM` here rather than shipped as the
    # free text the site writes ("May 12, 2019", "Dec. 27, 1997", "Julu 11,
    # 2018", "11-Feb-2015"). Parsing it in the pipeline means one parser for
    # the whole repo -- build_changelog's, which already knows every upstream
    # typo -- instead of a second, laxer copy in app.js that would drift from
    # it. It is also SMALLER: the raw strings cost 148 KB across 9751
    # documents, the normalized form 67 KB.
    #
    # Day precision is dropped because nothing displays it. The changelog
    # buckets by month or coarser, and the row shows "Jun 2024"; keeping the
    # day would cost 29 KB to render nothing. build_changelog still reads the
    # raw field from the inventory, so its own bucketing is unaffected.
    if ceiling is not None:
        when = parse_update(record.get("latest_update") or "", ceiling)
        if when:
            page["meta"]["updated"] = when.strftime("%Y-%m")
    if not has_text:
        page["meta"]["empty_in_snapshot"] = True
    # Scanned sources the site links beside this document. NOT the exemplar it
    # was encoded from -- the site never claims that, and the same volume is
    # cited by every text excerpted from it. See pipeline/parse_scans.py.
    if scans:
        found = scans.get(record["doc_id"])
        if found:
            page["meta"]["scans"] = compact_scans(found)
    return page


def roll(node: dict) -> dict:
    stats = empty_stats()
    for child in node["children"]:
        accumulate(stats, roll(child))
    for page in node["pages"]:
        accumulate(stats, page["stats"])
    node["stats"] = stats
    node["children"].sort(key=lambda n: n["title"])
    node["pages"].sort(key=lambda p: p["title"])
    return stats


def build_by_location(records: list[dict], sizes: dict,
                      scans: dict[str, list[dict]] | None = None,
                      ceiling: "datetime.datetime | None" = None) -> dict:
    """Canonical placement: folder -> document.

    Called "folder" rather than "deity" because the axis is not uniform: the
    site's `Location` is a single flat list of directories that are *mostly*
    deities (devii, shiva, vishhnu, ganesha, raama, subrahmanya, hanumaana,
    deities_misc -- ~7000 documents) but also genre or corpus buckets that no
    deity governs (veda, upanishhat, purana, giitaa, yoga, and seven z_misc_*
    catch-alls -- ~1500). "by deity" would misfile the Vedas; "by location"
    leaks a server path into the UI, and "folder" is what the thing is.

    Flat by design: the folder node is the only level. The page's
    `Sublocation` field looks like a second one but is not -- for ~99% of
    documents it merely repeats the location, and every value that differs is
    either a one-off upstream slip (`umamaheshvara` filed under devii saying
    `shiva`; `rudram` under shiva saying `veda`), a capitalization difference
    (`purana`/`purANa`, 42 vs 17), or the 817 `z_misc_general` documents whose
    field says `misc` where the directory says `general`. Branching on it
    produced twelve sidebar rows, none of which subdivided anything. The field
    is still carried in the inventory as a record of the page; it just does not
    shape the tree.
    """
    root = make_node("loc", "by folder")
    locations: dict[str, dict] = {}

    for record in records:
        loc = record["location"]
        node = locations.get(loc)
        if node is None:
            node = make_node(f"loc:{loc}", LOCATION_LABELS.get(loc, loc))
            locations[loc] = node
            root["children"].append(node)

        node["pages"].append(make_page(record, sizes, scans=scans,
                                       ceiling=ceiling))

    roll(root)
    return root


def build_by_listing(records: list[dict], sizes: dict,
                     listings: list[dict]) -> dict:
    """The site's own 87 browsable pages.

    Between the two extremes: `Location` is canonical but singular, and
    `Category` is multi-valued but uncontrolled free text. The listing pages are
    both multi-valued *and* curated by the site, which makes this the honest
    cross-cutting axis -- see notes/site-structure.md.

    Like the category branch, a document appears under each page it belongs to,
    so nodes hold lightweight refs and per-node stats count DISTINCT documents.
    """
    root = make_node("lst", "by topic")
    held = {record["doc_id"]: record for record in records}

    for listing in listings:
        # Listings enumerate the live site; we only have the snapshot's
        # documents. Anything unheld is dropped rather than emitted as a
        # dangling ref the frontend cannot resolve.
        doc_ids = [d for d in listing["doc_ids"] if d in held]
        if not doc_ids:
            continue

        node = make_node(f"lst:{listing['slug']}", listing["title"])
        stats = empty_stats()
        for doc_id in doc_ids:
            record = held[doc_id]
            measured = sizes.get(doc_id, {k: 0 for k in STAT_KEYS})
            accumulate(stats, {
                **measured,
                "count": 1,
                "text_count": 1 if measured["content_bytes"] > 0 else 0,
            })
            node["pages"].append({
                "id": f"doc:{doc_id}@{listing['slug']}",
                "type": "page",
                "title": record["title"] or record["stem"],
                "ref": f"doc:{doc_id}",
            })
        node["stats"] = stats
        node["pages"].sort(key=lambda p: p["title"])
        root["children"].append(node)

    root["children"].sort(key=lambda n: n["title"])
    # Distinct documents across the whole branch, NOT the sum of its nodes:
    # membership overlaps, so summing counts a text once per page it sits on.
    root["stats"] = distinct_stats(
        {d for lst in listings for d in lst["doc_ids"] if d in held}, sizes)
    return root


def distinct_stats(doc_ids: set[str], sizes: dict) -> dict:
    """Totals over a set of documents, each counted exactly once."""
    stats = empty_stats()
    for doc_id in doc_ids:
        measured = sizes.get(doc_id, {k: 0 for k in STAT_KEYS})
        accumulate(stats, {
            **measured,
            "count": 1,
            "text_count": 1 if measured["content_bytes"] > 0 else 0,
        })
    return stats


def load_live_stems(path: Path) -> set[str] | None:
    """Stems that answered 2xx/3xx when `make check-scans` last ran.

    Returns None when no liveness file exists, which the callers read as "no
    filtering" -- an unchecked build still produces links, it just cannot
    promise they resolve.
    """
    if not path.exists():
        return None
    live = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if 200 <= (row.get("status") or 0) < 400:
                live.add(row["stem"])
    return live


def stamp_version(log_path: Path, version_path: Path, tree_path: Path) -> str | None:
    """Write when the corpus was fetched into docs/VERSION.

    `__content_version__` is the date the newest page in the corpus was
    fetched, read from the fetch journal -- the scrape records its own date, so
    nothing needs maintaining by hand. It sat at "2025-02-16" for months
    because it was hand-maintained and the snapshot it named had long since
    stopped being what `build` read.

    `__data_version__` is today: when the pipeline last ran.

    Only stamped for the real track. The snapshot builder writes its own file
    and must not relabel the site as 18 months old.
    """
    if tree_path != TREE_PATH or not log_path.exists():
        return None
    newest = ""
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            fetched = json.loads(line).get("fetched_at") or ""
            if fetched > newest:
                newest = fetched
    if not newest:
        return None
    content = newest[:10]

    lines = []
    if version_path.exists():
        lines = version_path.read_text(encoding="utf-8").splitlines()
    fields = {}
    for line in lines:
        if "=" in line:
            key, _, value = line.partition("=")
            fields[key.strip()] = value.strip().strip("\"'")
    fields["__data_version__"] = datetime.date.today().isoformat()
    fields["__content_version__"] = content
    fields.setdefault("__code_version__", "0.1.0")

    version_path.write_text("".join(
        f'{k} = "{v}"\n' for k, v in (
            ("__code_version__", fields["__code_version__"]),
            ("__data_version__", fields["__data_version__"]),
            ("__content_version__", fields["__content_version__"]))),
        encoding="utf-8")
    return content


def summarize_scans(rows: list[dict]) -> dict:
    """Scan links -> the counts tree.json publishes.

    Deliberately counts `stem` rather than `url`: page-anchored archive.org
    links differ per document while naming one book, so counting URLs would
    report the same volume several times over.

    `rows` is expected to be live-filtered already (see main). 88 of the 891
    stems 404 or fail to connect, and a dead link is not a scanned source the
    reader can reach -- publishing it would be a claim about the site's markup
    rather than about available scans.
    """
    kinds = sorted({row["kind"] for row in rows})
    return {
        "sources": len({row["stem"] for row in rows}),
        "links": len(rows),
        "documents": len({row["doc_id"] for row in rows if row["doc_id"]}),
        "by_kind": {kind: len({row["stem"] for row in rows
                               if row["kind"] == kind})
                    for kind in kinds},
    }


def build(records: list[dict], sizes: dict,
          listings: list[dict] | None = None,
          scans: dict[str, list[dict]] | None = None,
          ceiling: "datetime.datetime | None" = None) -> dict:
    root = make_node("root", "संस्कृतदस्तावेजाः")
    # Only the location branch carries page objects; the listing branch holds
    # `ref` nodes that borrow them client-side (see rehydrate() in app.js), so
    # the scans reach both axes from this one attachment.
    branches = [build_by_location(records, sizes, scans, ceiling)]
    if listings:
        branches.append(build_by_listing(records, sizes, listings))
    root["children"] = branches
    # Deliberately NOT roll(root): the branches cover the same documents, so
    # summing them would multiply every figure. The corpus totals are the
    # location branch's, which reaches each document exactly once.
    root["stats"] = dict(branches[0]["stats"])
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path,
                        default=SITE_INVENTORY_PATH)
    parser.add_argument("--sizes", type=Path, default=SITE_SIZES_PATH)
    parser.add_argument("--listings", type=Path,
                        default=SITE_LISTINGS_PATH)
    parser.add_argument("--scans", type=Path, default=SCANS_PATH)
    parser.add_argument("--liveness", type=Path, default=SCAN_LIVENESS_PATH)
    parser.add_argument("--out", type=Path, default=TREE_PATH)
    parser.add_argument("--text-extract", type=Path, default=TEXT_EXTRACT_DIR,
                        help="rivulet's cleaned plain text, read ONLY to set "
                             "each document's `has_text` flag. Absent is fine: "
                             "the flag is then omitted.")
    parser.add_argument("--log", type=Path, default=TEXT_LOG_PATH,
                        help="fetch journal the content date comes from")
    parser.add_argument("--corpus-date", default=None,
                        help="YYYY-MM-DD the corpus was captured; caps every "
                             "document date. Defaults to the newest fetch in "
                             "--log. build_snapshot_tree passes the "
                             "snapshot's own date.")
    args = parser.parse_args()

    if not args.inventory.exists():
        raise SystemExit(
            f"missing {args.inventory}; run `make parse-site` first.")
    if not args.sizes.exists():
        raise SystemExit(
            f"missing {args.sizes}; run `make count-sizes` first.")
    if not args.listings.exists():
        raise SystemExit(
            f"missing {args.listings}; run `make parse-listings-site` first.")

    global _HAS_TEXT
    _HAS_TEXT = load_has_text(args.text_extract)
    if _HAS_TEXT is not None:
        print(f"  {len(_HAS_TEXT)} documents have extracted text on disk")

    records = [json.loads(line) for line in args.inventory.open(encoding="utf-8")]
    sizes = load_sizes(args.sizes)
    listings = [json.loads(line) for line in args.listings.open(encoding="utf-8")]

    # Loaded before the build: the counts go in `all_stats`, but the links
    # themselves have to reach each page's meta as it is made.
    scan_rows = []
    if args.scans.exists():
        scan_rows = [json.loads(line)
                     for line in args.scans.open(encoding="utf-8")]
    # Live-only, in the interface and in the exported count alike. Anything
    # that 404s or refuses to connect is dropped here, once, so the rendered
    # links and `pdf_count` cannot disagree about what exists.
    live_stems = load_live_stems(args.liveness)
    if live_stems is not None:
        before = len(scan_rows)
        scan_rows = [r for r in scan_rows if r["stem"] in live_stems]
        dropped = before - len(scan_rows)
    else:
        dropped = None
    by_doc = {}
    for row in scan_rows:
        if row["doc_id"]:
            by_doc.setdefault(row["doc_id"], []).append(row)

    # The date ceiling is per-track and cannot be a constant: every `Latest
    # update` after the corpus was captured is an upstream typo. Ours comes
    # from the fetch journal -- the same source `__content_version__` is
    # stamped from, so a row's date and the topbar cannot drift apart -- while
    # build_snapshot_tree passes the snapshot's own 2025-02-16. Hardcoding
    # either one rewrites the other track's genuinely-later documents.
    ceiling = (datetime.datetime.fromisoformat(args.corpus_date)
               .replace(tzinfo=datetime.timezone.utc)
               if args.corpus_date else corpus_date(args.log))

    root = build(records, sizes, listings, by_doc, ceiling)
    payload = {"root": root, "all_stats": root["stats"]}

    # Scanned sources, if `make parse-scans` has run. Only the counts go in --
    # the 5073 links themselves are ~700 KB and nothing on screen reads them
    # yet, so publishing them would repeat the size mistake this file exists to
    # avoid. `scans.jsonl` holds the detail when it is wanted.
    #
    # `sources` counts distinct scanned books, NOT links: one volume cited by
    # forty stotras excerpted from it is one source. It is also not "the scan
    # this etext came from" -- the site never claims that. See parse_scans.py.
    if scan_rows:
        payload["scans"] = summarize_scans(scan_rows)
        # `pdf_count` in all_stats is what Sāgarasaṅgama reads (CONTRACT.md);
        # the `scans` block above is this Atlas's own detail. Deduplicated by
        # stem, so a volume cited by forty stotras counts once -- the same
        # judgment sanskrit-wikisource makes for a work cited from several
        # pages, and the reason the definition lives here rather than there.
        payload["all_stats"]["pdf_count"] = payload["scans"]["sources"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))

    stats = root["stats"]
    for branch in root["children"]:
        label = branch["title"] + ":"
        print(f"{label:14}{len(branch['children']):5} nodes, "
              f"{branch['stats']['count']} distinct documents")
    print(f"documents:    {stats['count']}  ({stats['text_count']} with text)")
    for key in STAT_KEYS:
        print(f"{key + ':':16}{stats[key]:,}")
    if stats["transliterated_bytes"]:
        ratio = stats["content_bytes"] / stats["transliterated_bytes"]
        print(f"deva:iast     {ratio:.3f}x")
    if "scans" in payload:
        scans = payload["scans"]
        note = ("live-checked" if dropped is not None
                else "UNCHECKED -- run `make check-scans`")
        print(f"scans:        {scans['sources']} distinct sources on "
              f"{scans['documents']} documents ({note})")
        if dropped:
            print(f"              {dropped} links dropped as not live")
    stamped = stamp_version(args.log, VERSION_PATH, args.out)
    if stamped:
        print(f"content date: {stamped} (from {args.log.name})")
    print(f"wrote:        {args.out} "
          f"({args.out.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
