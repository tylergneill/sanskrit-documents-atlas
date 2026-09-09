"""Do the linked scans still resolve?

**The implementation lives in `rivulet`**, which is private; this module is a
runner so that `python -m pipeline.check_scans` and the Makefile target that
wraps it keep working. See `pipeline/fetch.py` for the boundary and for what
this repo can still do without the package installed.
"""

from pipeline.fetch import check_scans_main

if __name__ == "__main__":
    check_scans_main()()
