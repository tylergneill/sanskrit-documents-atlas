"""The site's change log -> data/metadata_cache/whatisnew/. About six requests.

**The implementation lives in `rivulet`**, which is private; this module is a
runner so that `python -m pipeline.fetch_whatisnew` and the Makefile target
that wraps it work like the other fetchers. Parsing the cache needs no network
and no rivulet: see `pipeline/parse_whatisnew.py`.
"""

from pipeline.fetch import fetch_whatisnew_main

if __name__ == "__main__":
    fetch_whatisnew_main()()
