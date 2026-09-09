#!/usr/bin/env python3
"""Local dev server for docs/, gzip-compressing responses and setting
Cache-Control so repeated reloads during iteration (and testing over an
ngrok tunnel on a mobile data plan) don't re-transfer the full uncompressed
tree.json/changelog.json on every load. python -m http.server does neither.

## `--fulltext` is localhost-only, and deliberately not publishable

`--fulltext` exposes the extracted corpus text at `/text/<doc_id>`, so the
frontend can offer a "txt" link beside each document.

**That text is never published.** It lives outside `docs/` -- under the
gitignored `data/text_extract/` -- so no build step and no deploy can pick it
up, and GitHub Pages serves `docs/` alone. Only this dev server can reach it,
and only when explicitly asked, bound to 127.0.0.1.

This corpus's ids ARE paths (`doc_devii/annapUrNAstotram`), so unlike the
sibling Atlases a filename could in principle be derived from one. It is not:
requests are resolved through a prebuilt index instead, so no user-supplied
string ever reaches the filesystem and `/text/../../etc/passwd` finds no key.
"""
import argparse
import gzip
import re
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

PORT = 8003

# Where the corpus text lives, relative to the repo root (NOT docs/).
TEXT_DIR = "data/text_extract"
TEXT_PREFIX = "/text/"
CACHE_MAX_AGE = 60  # seconds; short, so edits during iteration aren't stale for long
COMPRESSIBLE_SUFFIXES = {".json", ".js", ".html", ".css", ".svg"}


# Set by --snapshot: serve snapshot_tree.json wherever the frontend asks for
# tree.json. A SERVE-time choice, never a build-time one -- both builders always
# write their own file, and app.js requests the same path either way.
SERVE_SNAPSHOT = False


def load_text_index(root: Path) -> dict[str, Path]:
    """doc_id -> its extracted .txt, for every file actually on disk.

    Built by walking the extract rather than by trusting the tree: the tree
    lists 30039 documents and only ~9.7k are cached, so presence on disk is
    the only honest answer to "can this be served".
    """
    base = root / TEXT_DIR
    if not base.is_dir():
        return {}
    return {
        str(path.relative_to(base).with_suffix("")): path
        for path in base.rglob("*.txt")
    }



# "Local" means this machine or this LAN, matching docs/local-links.js:
# browsing from a phone at 192.168.1.x is a normal way to work here.
_LOCAL_ORIGIN_RE = re.compile(
    r"^https?://(localhost|127\.\d+\.\d+\.\d+|\[::1\]|"
    r"10\.[\d.]+|192\.168\.[\d.]+|172\.(1[6-9]|2\d|3[01])\.[\d.]+)"
    r"(:\d+)?$"
)


def _is_local_origin(origin: str) -> bool:
    return bool(origin) and bool(_LOCAL_ORIGIN_RE.match(origin))


class CachingGzipHandler(SimpleHTTPRequestHandler):
    fulltext = False
    text_index: dict[str, Path] = {}

    def do_HEAD(self):
        # The frontend probes `/text/` to learn whether this server offers the
        # corpus at all. A header, rather than the shape of a 404, so the page
        # never has to guess from a status a static host could also produce.
        if self.path.split("?")[0].startswith(TEXT_PREFIX):
            self.send_response(404)
            self.send_header("X-Fulltext-Mode", "on" if self.fulltext else "off")
        # Sagarasangama runs on another port, so its probe and its `txt`
        # links are cross-origin. Allowed narrowly: only the /text/ route,
        # only in fulltext mode, and only for a localhost/private-network
        # origin -- the same "local means this machine or this LAN" rule
        # local-links.js uses. Nothing here widens what the PUBLISHED site
        # can reach, because the published site has no /text/ route at all.
        origin = self.headers.get("Origin", "")
        if self.fulltext and _is_local_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Expose-Headers", "X-Fulltext-Mode")

            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_HEAD()

    def _serve_text(self, doc_id):
        """`/text/<doc_id>` -> the extracted text, as UTF-8 plain text."""
        path = self.text_index.get(unquote(doc_id).strip("/"))
        if path is None:
            self.send_error(404, "no text for that document")
            return
        raw = path.read_bytes()
        body = gzip.compress(raw) if "gzip" in self.headers.get("Accept-Encoding", "") else raw
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        # Sagarasangama runs on another port, so its probe and its `txt`
        # links are cross-origin. Allowed narrowly: only the /text/ route,
        # only in fulltext mode, and only for a localhost/private-network
        # origin -- the same "local means this machine or this LAN" rule
        # local-links.js uses. Nothing here widens what the PUBLISHED site
        # can reach, because the published site has no /text/ route at all.
        origin = self.headers.get("Origin", "")
        if self.fulltext and _is_local_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Expose-Headers", "X-Fulltext-Mode")

        if body is not raw:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def translate_path(self, path):
        if SERVE_SNAPSHOT and path.split("?")[0].endswith("/data/tree.json"):
            path = path.replace("/data/tree.json", "/data/snapshot_tree.json")
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", f"max-age={CACHE_MAX_AGE}")
        super().end_headers()

    def do_GET(self):
        route = self.path.split("?")[0]
        if route.startswith(TEXT_PREFIX):
            self._serve_text(route[len(TEXT_PREFIX):])
            return

        path = self.translate_path(self.path)
        accepts_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        if accepts_gzip and Path(path).suffix in COMPRESSIBLE_SUFFIXES and Path(path).is_file():
            self._serve_gzipped(path)
        else:
            super().do_GET()

    def _serve_gzipped(self, path):
        raw = Path(path).read_bytes()
        compressed = gzip.compress(raw)
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(compressed)))
        self.end_headers()
        self.wfile.write(compressed)


def main():
    global SERVE_SNAPSHOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", type=int, default=PORT)
    parser.add_argument("--snapshot", action="store_true",
                        help="serve snapshot_tree.json (8547 documents, the "
                             "earlier Feb-2025 scrape) in place of "
                             "tree.json (9756, our own fetch)")
    parser.add_argument("--fulltext", action="store_true",
                        help="serve the extracted corpus text at "
                             "/text/<doc_id>, so the frontend shows a `txt` "
                             "link. LOCALHOST ONLY -- the text lives outside "
                             "docs/ and is never published")
    args = parser.parse_args()
    SERVE_SNAPSHOT = args.snapshot

    root = Path(__file__).resolve().parent
    CachingGzipHandler.fulltext = args.fulltext
    if args.fulltext:
        CachingGzipHandler.text_index = load_text_index(root)

    # Pin the served directory to docs/ rather than inheriting the caller's
    # cwd, so running this from the repo root cannot expose data/.
    handler = partial(CachingGzipHandler, directory=str(root / "docs"))

    # Loopback in fulltext mode: the corpus text is not ours to hand out.
    host = "127.0.0.1" if args.fulltext else ""
    server = HTTPServer((host, args.port), handler)
    which = "SNAPSHOT tree (Feb-2025, 8547 docs)" if args.snapshot else "tree.json"
    print(f"Serving docs/ on http://localhost:{args.port} -- {which} "
          f"(gzip + Cache-Control: max-age={CACHE_MAX_AGE})")
    if args.fulltext:
        count = len(CachingGzipHandler.text_index)
        print(f"  fulltext: {count} documents at /text/<doc_id> "
              f"-- LOCALHOST ONLY, never published")
        if not count:
            print("            (none found -- run `make extract-text`)")
    server.serve_forever()


if __name__ == "__main__":
    main()
