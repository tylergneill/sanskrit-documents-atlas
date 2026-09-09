"""Every networked entry point this Atlas has, and none of them live here.

Acquisition moved to the private `rivulet` package on 2026-09-03. This module
is the one place this repo names it for *fetching* -- `fulltext.py` is the
same shim for text extraction -- and it never requires it.

## What this repo can still do alone

Everything that reads a cache already on disk:

    make parse            parse-listings    recount      build
    make changelog        audit             serve        parse-dump-2020

Those are the majority of the pipeline and they are unaffected. What needs
rivulet is anything that crosses the network:

    make fetch-metadata   the sitemap walk that writes catalogue.jsonl
    make fetch-text       the corpus itself
    make check-scans      are the linked scans still resolving?

**A checkout without rivulet cannot build the corpus from scratch.** That is
accepted and deliberate: there is no meaningful way to obtain the data without
the acquisition code, so the honest failure is an immediate, explained exit
rather than a pipeline that half-runs. If `data/` is already populated, every
offline target works and the atlas builds normally.

## The exit code

    0   it worked
    1   it ran and failed
    2   the machinery is not installed

2 is not a bug to fix on this machine. It means "this checkout cannot reach the
network, and that is a supported configuration."
"""

import sys

EXIT_NOT_INSTALLED = 2

_MISSING = """\
acquisition machinery not installed.

Fetching lives in the private `rivulet` package, which is not present in this
environment. Everything that reads the existing cache still runs: `make parse`,
`make build`, `make changelog`, `make audit` and `make serve` are unaffected.

To enable it:  pip install -e ../../rivulet
"""


def _load(dotted: str, name: str):
    """Import `name` from a rivulet module, or exit 2 if the package is absent.

    Imported at the point of use rather than at module load, so that merely
    importing this shim never depends on rivulet being installed -- the same
    discipline `fulltext.py` follows.
    """
    try:
        module = __import__(dotted, fromlist=[name])
    except ImportError:
        print(_MISSING, file=sys.stderr)
        raise SystemExit(EXIT_NOT_INSTALLED)
    return getattr(module, name)


def fetch_metadata_main():
    return _load("rivulet.extract.sanskrit_documents.fetch_metadata", "main")


def fetch_text_main():
    return _load("rivulet.extract.sanskrit_documents.fetch_fulltext", "main")


def check_scans_main():
    return _load("rivulet.verify.sanskrit_documents.check_scans", "main")


def available() -> bool:
    """Whether networked work is possible here. Asks, rather than exits."""
    try:
        import rivulet  # noqa: F401
    except ImportError:
        return False
    return True
