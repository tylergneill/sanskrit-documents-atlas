"""Stage 3c: data/fulltext_cache/ -> data/text_extract/. No network.

The cached pages `fetch_text.py` wrote, with everything but the work's body
stripped away, transliterated to IAST. One `<doc_id>.txt` per document,
mirroring the cache's one-directory-per-category layout.

**IAST, matching `recount_sizes.py`** -- which measures `transliterated_bytes`
off this same body -- so the text on disk and the byte figure the tree
publishes are in one script. `--no-transliterate` writes Devanagari instead,
for a machine without rivulet's `[translit]` extra.

**The extraction itself is not here.** It lives in the private `rivulet`
package, which owns every rule about what counts as the body -- selection by
`id="content"`, exclusion of the `<pre class="inf">` metadata block, tag
removal, entity unescaping. This module is the invocation: it resolves the two
paths, calls in, and reports. See `pipeline/fulltext.py` for why the dependency
is optional and what exit 2 means.

Both directories are under the gitignored `data/`; this repo publishes no text.

    make extract-text
    make extract-text ARGS="--cache data/fulltext_cache --out data/text_extract"
"""

import argparse
from pathlib import Path

from pipeline.fulltext import load_extractor

CACHE_DIR = Path("data/fulltext_cache")
TEXT_EXTRACT_DIR = Path("data/text_extract")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache", type=Path, default=CACHE_DIR,
                        help=f"cached pages to read (default {CACHE_DIR})")
    parser.add_argument("--out", type=Path, default=TEXT_EXTRACT_DIR,
                        help=f"where to write the text tree "
                             f"(default {TEXT_EXTRACT_DIR})")
    parser.add_argument("--no-transliterate", action="store_true",
                        help="write the Devanagari body instead of IAST. The "
                             "transliterator is an optional dependency, so "
                             "this is a supported configuration, not an error.")
    args = parser.parse_args()

    # Exits 2 before touching the disk if rivulet is absent, so a public
    # checkout gets the "not installed" message rather than a half-run.
    extract_cache = load_extractor()

    if not args.cache.is_dir():
        raise SystemExit(
            f"no cache at {args.cache} -- run `make fetch-text` first.")

    summary = extract_cache(args.cache, args.out,
                            transliterate=not args.no_transliterate)

    print(f"written:   {summary['written']} documents "
          f"({'Devanagari' if args.no_transliterate else 'IAST'})")
    if summary["empty"]:
        print(f"empty:     {summary['empty']} (body block held nothing)")
    if summary["no_body"]:
        print(f"no body:   {summary['no_body']} (metadata-only pages)")
    print(f"content:   {summary['content_bytes']:,} bytes (Devanagari)")
    if summary["translit_bytes"]:
        print(f"IAST:      {summary['translit_bytes']:,} bytes")
    print(f"wrote:     {args.out}")


if __name__ == "__main__":
    main()
