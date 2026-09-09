"""Normalize the free-text `Category` field into concepts.

The field is a comma-separated bag of tags on every document. It is *not* a
controlled vocabulary: on our own 9756-document fetch, 366 raw spellings reduce
to 317 concepts, of which only 85 name a real `/sanskrit/<slug>/` listing page.
(The 332/284 figures this docstring used to quote were the 8547-document
Feb-2025 snapshot's.) The rest name nothing
browsable, and a large share are not categories at all -- authors, source
works, and encoder names filed in the same field with no marker saying which.

Normalization is two-stage:

1. **Mechanical** -- fold ITRANS long-vowel and case variants
   (`durgA`/`durga`, `devI`/`devii`).
2. **Explicit** -- a hand-checked alias table for variants the mechanical rule
   cannot reach: typos (`kavaha`), doubled consonants (`linggapurANa`),
   and stem variation (`upanishad`/`upanishhat`).

**This table serves BOTH corpora, so judge it against both.** `ALIASES` is
applied to whichever docroot is being parsed -- the Feb-2025 snapshot and our
own 2026-08 fetch alike -- and the site fixes its own typos over time. An entry
whose key has zero occurrences in `fulltext_cache` is therefore *not* dead: it
may be earning its keep on the snapshot track, as `sahsaranAma` does (present
in the snapshot's `doc_devii/jAnakIsahasranAmastotram2.html`, fixed upstream by
2026-08). Grepping only the current fetch and pronouncing an entry unused is a
mistake this docstring exists to prevent. The converse holds too: a spelling
the site introduced after Feb 2025 will be attested only in the current fetch.

Published figures are the other way round -- `intro_stats()` reads
`site_inventory.jsonl`, so every count and every example quoted in
`docs/about.html` must be attested in the CURRENT fetch, not the snapshot.

**Which spelling survives a merge**: the slug spelling where one exists, else
the majority spelling. This is a display decision -- the surviving form is what
the frontend's category filter offers as an option -- so getting it backwards
shows readers a spelling almost none of their documents use. Three entries were
merging correctly but surviving as the *minority* form and were flipped
2026-08-13 (`dhyAna` 3 -> `dhyAnam` 100, and likewise `panchAshat`,
`bRihaddharmapurANa`).

The slug-spelling half of that rule has one limit, found 2026-08-26: a slug is
a URL path, not necessarily a spelling anyone tags with. No document carries
the literal `gita` -- the raw spellings are `giitaa` (135) and `gItA` (110) --
so the survivor is a label no document typed. That is fine, and the rule it
seemed to break is narrower than it looked: what must not happen is an option
matching NOTHING. `gita` is the fold target for both raw spellings, so the
option matches 137 documents; only a survivor outside the fold would match
zero.

**Normalization belongs here, not in the frontend.** `app.js` reads
`meta.categories` as already-canonical strings and never folds, aliases, or
de-duplicates them; the option list it shows is exactly what this module
produced. Add a variant here and it disappears from the UI on the next build.

**The 87 slugs are ground truth.** Where the mechanical rule would merge two
distinct slugs, the literal spelling wins instead -- unless the pair is listed
in `ALIASES` below, which overrides the guard for spellings that are the same
*word* even though the site also maintains them as two separate topic pages.
Never relax the guard itself without re-checking against the slug list.

**The test is semantic, not statistical.** A pair merges here only if there is
no possible meaning under which the alternate spelling names a different
thing -- not merely because their tagging overlaps or diverges in practice.
`vishhnu` and `vishnu` are one noun spelled two ways (`shh` for retroflex `s`
is the site's own ITRANS convention); nothing about the spelling can select a
narrower or broader Vishnu, so they merge. The survivor here is `vishnu`, the
minority spelling (919 against `vishhnu`'s 1813) -- a deliberate exception to
the majority rule, matching what `parse_listings.ALIAS_SURVIVORS` already
picked for the topic-page pair. The same reasoning merges `gItA` and `giitaa`
into `gita`: one word (feminine "gItA", song), three transliterations, and
`giitaa`'s 135 documents are a strict subset of `gita`'s 138.

**Deliberately NOT merged**, because a semantic distinction is possible:

    vishnu_misc   "vishnu's other avataras" (29) -- a different name string,
                  not a spelling of "vishnu", so no rule reaches it anyway.
    gItam         the neuter "gItam", not the feminine "gItA"/"giitaa" --
                  its members are the Bhagavata Purana's individual named
                  gItā/gītam chapters (avadhUtagItA, bhrAmaragItA, ...), a
                  distinct sub-corpus with its own topic page, not a spelling
                  of the other two.
"""

import re

# Variants no vowel-folding rule can reach. Each was read off the full concept
# listing and checked against the slug list; the value is the surviving form.
ALIASES = {
    # typos -- single occurrences beside a well-attested spelling
    "sahsaranAma": "sahasranAma",
    "saharanAmAvalI": "sahasranAmAvalI",
    "aShTottrashatanAmAvalI": "aShTottarashatanAmAvalI",
    "pAravtI": "pArvatI",
    "kAshimIrashaivadarshanam": "kAshmIrashaivadarshanam",
    "dvAdhasha": "dvAdasha",
    "kavaha": "kavacha",
    "vAmapurANa": "vAmanapurANa",
    # doubled / dropped consonants
    "linggapurANa": "lingapurANa",
    "vishvanAthachakravartina": "vishvanAthachakravartin",
    "moropant": "moropanta",
    "gurudeva": "gurudev",
    "raam": "raama",
    "ramana": "ramaNa-maharShi",
    "hanuman": "hanumaana",
    "shankara": "shankarAchArya",
    # stem variation on the same word. The surviving form is the slug spelling
    # where one exists, else the majority spelling -- counts in parentheses.
    "upanishad": "upanishhat",
    "upaniShat": "upanishhat",
    "upaniShad": "upanishhat",   # 1, the same stem-variation merge as the two above
    "bRihaddharmapurANa": "bRihaddharmapurANam",   # 1 -> 17
    "dhyAna": "dhyAnam",                            # 3 -> 100
    "panchAshat": "panchAshata",                    # 1 -> 6
    "pancha": "panchaka",                           # 2 -> 157, and a real slug
    "panchAshatnAmAvalI": "panchAshatanAmAvalI",
    "nAMAvalI": "nAmAvalI",
    # a stray period where a comma belonged, so the splitter kept one value
    "stotra. aShTaka": "stotra",
    # same word, two site slugs -- see the semantic-merge note above.
    #
    # This side of the arrow is the GROUPING KEY. The displayed spelling is
    # chosen separately, by `canonical_spellings` -- but where both spellings
    # are real slugs, as here, it defers to `parse_listings.ALIAS_SURVIVORS`,
    # which names `vishnu`. So this pair does ship `vishnu`, the minority
    # spelling (919 against `vishhnu`'s 1814), matching the topic page kept for
    # the same pair.
    #
    # It did not always. Until 2026-09-07 `canonical_spellings` built its slug
    # lookup by iterating a set, so the winner was whichever came last and
    # varied BETWEEN PROCESSES -- 1,815 documents flipped spelling from one
    # build to the next, and `tree.json` was not reproducible. If you are
    # changing that function, the invariant is: same inputs, same spelling.
    "vishhnu": "vishnu",
    # `giitaa` is a strict subset of `gita`: 135 documents, all 138 of `gita`'s
    # minus three (gaNeshagItAsArastotram, sannyaasagiitaa, saptashlokIgItA).
    # One page with three entries added, so `gita` is the survivor -- the
    # superset, and what ALIAS_SURVIVORS already names.
    "giitaa": "gita",
    "gItA": "gita",
}


def mechanical(value: str) -> str:
    """Case- and length-insensitive key. Not for display."""
    key = re.sub(r"[^a-z0-9]", "", value.lower())
    return key.replace("aa", "a").replace("uu", "u").replace("ii", "i")


def build_key(slugs: set[str]):
    """Return a key() closure guarded against collapsing two real slugs."""
    collisions: dict[str, list[str]] = {}
    for slug in slugs:
        collisions.setdefault(mechanical(slug), []).append(slug)
    protected = {s for group in collisions.values() if len(group) > 1
                 for s in group}

    def key(value: str) -> str:
        value = ALIASES.get(value, value)
        lowered = value.lower()
        # A protected spelling keys on itself unless ALIASES already resolved
        # it to the other slug (vishhnu -> vishnu, giitaa -> gita above), so
        # e.g. upanishad != upanishhat would stay apart without an alias.
        return lowered if lowered in protected else mechanical(value)

    return key


def split(raw: str) -> list[str]:
    """The raw field -> its individual values."""
    return [v.strip() for v in raw.split(",") if v.strip()]
