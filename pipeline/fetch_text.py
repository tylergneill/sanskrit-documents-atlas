"""Tier 2: one request per document in the catalogue.

**The implementation lives in `rivulet`**, which is private; this module is a
runner so that `python -m pipeline.fetch_text` and the Makefile target that
wraps it keep working. See `pipeline/fetch.py` for the boundary and for what
this repo can still do without the package installed.
"""

from pipeline.fetch import fetch_text_main

if __name__ == "__main__":
    fetch_text_main()()
