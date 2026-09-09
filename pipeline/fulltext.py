"""The one place this repo mentions `rivulet`, and it never requires it.

Clean-text output lives in a private package. This Atlas is public and **runs
to completion without it**: the catalogue, the page fetch, all the parsing, and
the sizes are here. What rivulet adds is body-only plain text -- writing the
corpus out as files, which is a publishing act rather than a build step.

Unlike the other two Atlases, nothing *moved* out of this repo to make that
true. Its metadata (`<pre class="inf">` -- title, author, categories,
`latest_update`) exists only inside the fulltext pages, so the public pipeline
must keep fetching whole pages regardless. rivulet reads the cache that fetch
already wrote and derives the stripped text from it.

So the dependency is optional and one-way. `try: import rivulet` is the whole
mechanism, and the failure is a *distinct exit code* rather than a traceback:

    0   it worked
    1   it ran and failed
    2   the machinery is not installed

2 is not an error to be fixed on this machine. It means "this build cannot
produce fulltext output, and that is a supported configuration" -- which is
what lets a public checkout run `make` targets without pretending a private
package is missing by mistake.
"""

import sys

EXIT_NOT_INSTALLED = 2

_MISSING = """\
fulltext machinery not installed.

Text extraction lives in the private `rivulet` package, which is not present
in this environment. Everything else in this repo runs without it: the
catalogue, `make fetch-text`, the tree, and the byte sizes are all unaffected.

To enable it:  pip install -e ../../rivulet
"""


def load_extractor():
    """Return rivulet's `extract_cache`, or exit 2 if it is absent.

    Called at the point of use rather than at import, so that merely importing
    this module never depends on rivulet being installed.
    """
    try:
        from rivulet.extract.sanskrit_documents.text_extractor import extract_cache
    except ImportError:
        print(_MISSING, file=sys.stderr)
        raise SystemExit(EXIT_NOT_INSTALLED)
    return extract_cache


def available() -> bool:
    """Whether fulltext output is possible here. Asks, rather than exits.

    For callers that want to report or branch instead of stopping -- the
    `has_text` flag in the built tree, for instance.
    """
    try:
        import rivulet  # noqa: F401
    except ImportError:
        return False
    return True
