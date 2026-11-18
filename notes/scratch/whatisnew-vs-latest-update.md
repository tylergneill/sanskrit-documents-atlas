# whatisnew "date added" vs `Latest update`

**Status (2026-11-17):** measured once, analysis only. Nothing in the pipeline
or `docs/data/` changed. Re-derive with
`python notes/scratch/whatisnew_vs_latest_update.py` (documented in its
docstring); every figure below is its output.

**Question:** does a "date added" taken from the site's change log tell us
anything the per-document `Latest update` stamp does not? Inputs:
`data/whatisnew_events.jsonl` (12,853 events) and the 9,935 documents of the
November catalogue, each with its stamp as `meta.updated` in
`docs/data/tree.json` (9,926 have one).

- **added**: the earliest event with verb "added".
- **first**: the earliest event of any verb. Moved or renamed documents lose
  their "added" line.
- Both are compared with the stamp at month precision.

## In plain terms

Of the 8,236 documents that have both a log "added" date and a stamp, here is
the log date relative to the stamp:

| | past (log earlier) | future (log later) | total |
|---|---:|---:|---:|
| **same month** | | | 6,676 (81%) |
| **within 3 months** | 151 | 405 | 556 (7%) |
| **more than 3 months** | 704 | 300 | 1,004 (12%) |

- **Past (855 in all)** is expected: the document was added first and the stamp
  moved on a later edit. These are the documents where the log adds real
  information.
- **Future, within 3 months (405)** looks like the gap between preparing a
  file and posting it.
- **Future, more than 3 months (300)**: 118 are the log's October 2010 start,
  a floor rather than a conflict. The other **182 are the real conflicts**,
  about 2% of the 8,236.

The other 1,699 documents have no "added" event (1,690) or no stamp (9).

## Results by bucket

| bucket | added | first |
|---|---:|---:|
| 1. no event | 1,690 | 596 |
| 2. same month as stamp | 6,676 | 7,095 |
| 3. earlier than stamp | 855 | 1,077 |
| 4a. later: opening-batch floor | 118 | 119 |
| 4b. later: real reversal | 587 | 1,039 |
| no stamp | 9 | 9 |

- **1,097** documents have "updated" events only and no "added" event.
- Of the 1,039 `first` reversals, **578** start with an "added" event and **461**
  with an "updated" one.

Real reversals (4b), gap in months (event minus stamp):

| gap | added | first |
|---|---:|---:|
| 1 | 278 | 307 |
| 2–3 | 127 | 149 |
| 4–6 | 47 | 59 |
| 7–12 | 46 | 72 |
| 13–24 | 20 | 41 |
| 25–60 | 16 | 51 |
| 61+ | 53 | 360 |

Medians: 2 months for `added`, 7 for `first`. The reversals cluster in a few
event months: 2018-05 (98), 2018-03 (91), 2019-10 (65), 2013-09 (56).

## What it means

- **Mostly the add date repeats the stamp.** 67% of documents (`added`) land
  in the same month. For those, the stamp is evidently the date the document
  went up and was never bumped.
- **It adds information for about 9–11%:** 855 documents (`added`) or 1,077
  (`first`) have a logged event before their stamp. These are the documents
  whose stamp moved on a later touch, which is the case the change-log dating
  exists for.
- **Most `added` reversals are short.** 405 of 587 are 1–3 months, and they
  bunch in a few months (2018-03, 2018-05). That pattern is consistent with a
  stamp set when a file was prepared and a log entry written when a batch was
  posted. It looks like posting lag, not a conflict.
- **The long `first` reversals are mostly unbumped stamps.** 360 are 61+
  months, and 461 of the 1,039 begin with an "updated" event. Those are
  documents touched after their stamp, where the stamp was never updated.
  That makes them evidence that `Latest update` lags, not that the log is
  wrong.
- **For dating, `first` is the right floor, not `added`.** It covers 1,094
  more documents (596 vs 1,690 with no event), and the 1,097 "updated only"
  documents would otherwise be undated by the log.

## The floor rule had to move from 2010-04 to 2010-10

The brief defined the floor as "first event is the 2010-04 log-start batch
while stamp is before 2010-04". **Keyed to 2010-04, that bucket is empty (0
and 0).** The log's header says "since April 2010" and its earliest entry is
2010-04-25, but April holds only 5 events. The bulk backfill is a single day,
**2010-10-03, with 421 events** (211 added and 210 updated). Every reversal in
that month has a stamp from before 2010-04. So the script keeps the rule's
intent (stamp predates the log; event is the opening batch) but keys the batch
to 2010-10. It also checks both months against the events file, so the rule
can't drift silently.

Related: `whatisnew.md` describes pre-2010 stamps as placeable only "by April
2010". The effective floor for most of them is October 2010.

## Not covered

- **476 doc_ids in the log aren't in the November catalogue** (deleted or
  renamed). They're outside this comparison by construction.
- **Month precision only.** Same-month pairs might still differ by days.

## Script output

Samples are 10 per bucket, seeded (`random.Random(0)`) and sorted. Events are
listed as `a:` (added) and `u:` (updated) with their months.

```
documents in the folders branch: 9935
  with a stamp: 9926
documents with any whatisnew event: 9338
event doc_ids not in the catalogue: 476
log start (earliest event month): 2010-04, 5 events in that month
opening batch: 2010-10-03, 421 events in one day
floor bucket if keyed to 2010-04 instead: added 0, first 0
updated events only, no added event: 1097

added vs stamp, plain terms (8236 documents with both):

| | past (log earlier) | future (log later) | total |
|---|---:|---:|---:|
| same month | | | 6676 |
| within 3 months | 151 | 405 | 556 |
| more than 3 months | 704 | 300 | 1004 |

  of which future, more than 3 months, opening-batch floor: 118

| bucket | added | first |
|---|---:|---:|
| no_event | 1690 | 596 |
| same | 6676 | 7095 |
| earlier | 855 | 1077 |
| later_floor | 118 | 119 |
| later_real | 587 | 1039 |
| no_stamp | 9 | 9 |
| total | 9935 | 9935 |

first / later_real by verb of the first event: added 578, updated 461

Real reversals: gap in months (event minus stamp)

| gap | added | first |
|---|---:|---:|
| 1 | 278 | 307 |
| 2-3 | 127 | 149 |
| 4-6 | 47 | 59 |
| 7-12 | 46 | 72 |
| 13-24 | 20 | 41 |
| 25-60 | 16 | 51 |
| 61+ | 53 | 360 |

added: median gap 2, max 324; most common event months: 2018-05 (98), 2018-03 (91), 2019-10 (65), 2013-09 (56), 2012-11 (38)

first: median gap 7, max 346; most common event months: 2018-05 (98), 2018-03 (91), 2019-10 (66), 2013-09 (57), 2014-12 (53)

Samples (10 per bucket, seeded, sorted)

added / no_event (1690):
  doc_deities_misc/rAmAnujavaibhavastotram  stamp=2022-06  events=u:2022-06
  doc_ganesha/vikaTastutiHkAmAsureNaproktam  stamp=2020-04  events=-
  doc_raama/manobodha-skt  stamp=2013-10  events=-
  doc_shiva/shivasutra  stamp=2025-10  events=u:2014-12,u:2017-05,u:2023-05,u:2023-09,u:2025-10
  doc_subrahmanya/subrahmaNyatrishatI  stamp=2009-07  events=-
  doc_upanishhat/iisha  stamp=1999-07  events=u:2014-12
  doc_vishhnu/chaturviMshatyavatArastotram3  stamp=2021-12  events=u:2015-08,u:2015-10,u:2017-11,u:2021-12
  doc_vishhnu/kakArAdikUrma108nAmastotram  stamp=2016-01  events=u:2016-02
  doc_z_misc_navagraha/jayAdityastotramskandapurANa  stamp=2018-02  events=-
  doc_z_misc_navagraha/shukrakavach  stamp=2005-02  events=u:2017-03,u:2018-11

added / same (6676):
  doc_deities_misc/vedAntadeshikamaNgalAshAsanam  stamp=2017-10  events=a:2017-10,u:2024-08
  doc_devii/devIpUjAvidhAnam  stamp=2017-05  events=a:2017-05
  doc_devii/devIsiddhapIThAnidevIbhAgavatam  stamp=2018-06  events=a:2018-06
  doc_devii/rAdhAvibhUtistotram  stamp=2025-03  events=a:2025-03
  doc_ganesha/gaNeshAShTakam8  stamp=2022-01  events=a:2022-01
  doc_shiva/IshvaraproktaMshivadharmAchArakathanam  stamp=2024-10  events=a:2024-10
  doc_shiva/shankarastotram5  stamp=2023-12  events=a:2023-12
  doc_shiva/shivastutiHdevIkRRitA  stamp=2023-09  events=a:2023-09
  doc_vishhnu/brahmakRRitaM12viShNustotram  stamp=2025-11  events=a:2025-11
  doc_z_misc_general/mantrabhajanAdinirUpaNam  stamp=2026-04  events=a:2026-04

added / earlier (855):
  doc_devii/aaryaa15  stamp=2022-12  events=a:2010-10,u:2010-10
  doc_devii/devIvighnaharastotram  stamp=2022-12  events=a:2020-10,u:2022-12
  doc_devii/reNukAkhaDgamAlAmantra  stamp=2024-04  events=a:2013-07,u:2024-04
  doc_devii/yoganAyikAsahasranAmastotram  stamp=2024-02  events=a:2018-02
  doc_shiva/maheshvaraprAtaHsmaraNastotram  stamp=2021-02  events=a:2020-12,u:2021-02
  doc_shiva/shivastutiH14  stamp=2021-05  events=a:2020-09,u:2021-03,u:2021-05
  doc_shiva/tANDaveshvarItAnDaveshvara108  stamp=2017-02  events=a:2016-11,u:2017-02
  doc_vishhnu/gopAladivyasahasranAmastotram  stamp=2024-03  events=a:2023-09,u:2024-03
  doc_z_misc_general/jayabhAratIvandebhAratIm2  stamp=2024-02  events=a:2023-12,a:2024-02
  doc_z_misc_general/utkaleShusaMskRRitacharchchA  stamp=2021-06  events=a:2021-05

added / later_floor (118):
  doc_deities_misc/bhaktaamara  stamp=2000-08  events=a:2010-10,u:2010-10
  doc_deities_misc/vyasa-8  stamp=2007-08  events=a:2010-10,u:2010-10,u:2012-07,u:2022-11
  doc_giitaa/bodhyagiitaa  stamp=1998-06  events=a:2010-10,u:2010-10,u:2013-01
  doc_giitaa/ganeshagita  stamp=2008-07  events=a:2010-10,u:2010-10
  doc_giitaa/suuryagiitaa  stamp=2008-10  events=a:2010-10,u:2010-10
  doc_raama/adhyaatmaRamkiShkindhA  stamp=2006-07  events=a:2010-10,u:2010-10,u:2013-06,u:2015-05,u:2015-08,u:2018-09
  doc_upanishhat/Ishaa_bhaashhya_Shankar  stamp=2001-05  events=a:2010-10,u:2010-10,u:2013-05,u:2014-08
  doc_upanishhat/amrtabindu_upan  stamp=1996-04  events=a:2010-10,u:2010-10,u:2016-01,u:2017-03,u:2021-03
  doc_veda/rudra  stamp=2000-06  events=a:2010-10,u:2010-10,u:2011-06,u:2017-05,u:2022-03
  doc_vishhnu/guruvaatapuriisha  stamp=1997-12  events=a:2010-10,u:2010-10,u:2017-01,u:2017-09,u:2021-10,u:2022-02

added / later_real (587):
  doc_devii/dakShiNAstotram  stamp=2018-03  events=a:2018-05
  doc_raama/rAmajAnakIstutiH  stamp=2018-03  events=a:2018-05
  doc_shiva/shivastutinArAyaNapaNDita  stamp=2013-04  events=a:2013-07
  doc_vishhnu/devaiHkRRitaMmahAviShNustotram  stamp=2021-04  events=a:2021-05
  doc_vishhnu/venkaTeshvaradvAdashapanjarikA  stamp=2012-07  events=a:2012-11,u:2015-12,u:2015-12,u:2021-05
  doc_vishhnu/viShNorakArAdyaShTottarashatanAmAvaliH  stamp=2018-04  events=a:2018-05
  doc_vishhnu/viThThalasahasranAmAvaliH  stamp=2018-04  events=a:2018-05
  doc_z_misc_general/kAlidAsaHjanejane  stamp=2019-09  events=a:2019-10
  doc_z_misc_general/sarveShAMnojananI  stamp=2019-09  events=a:2019-10
  doc_z_misc_general/smarachiraMhebhAratIya  stamp=2019-09  events=a:2019-10

added / no_stamp (9):
  doc_deities_misc/suryanamaskArmantra  stamp=None  events=u:2021-01
  doc_devii/bhadrakAlIkavacham2  stamp=None  events=a:2020-09
  doc_devii/laxmi1000  stamp=None  events=u:2011-11,u:2011-11,a:2012-01,u:2012-01,u:2016-07
  doc_devii/sarasvatistotra  stamp=None  events=a:2013-12,u:2026-04
  doc_shiva/sharabhasahasranAmastotra  stamp=None  events=a:2017-08,u:2017-08,u:2020-08
  doc_shiva/shivamangalAShTaka  stamp=None  events=a:2011-08
  doc_veda/sangyaanasuukta  stamp=None  events=u:2014-12,u:2025-02
  doc_z_misc_shankara/ekashloki  stamp=None  events=-
  doc_z_misc_subhaashita/subhash  stamp=None  events=u:2016-07

first / no_event (596):
  doc_devii/hAkinIsahasra  stamp=2009-05  events=-
  doc_devii/laghu16  stamp=2001-10  events=-
  doc_devii/navAksharI  stamp=2001-10  events=-
  doc_ganesha/gaNAdhipati5  stamp=2002-04  events=-
  doc_hanumaana/hanuman40  stamp=2010-10  events=-
  doc_shiva/mrtyumaanasa  stamp=2008-07  events=-
  doc_shiva/svarNAkarShaNabhairavastotram2  stamp=2022-07  events=-
  doc_z_misc_major_works/natya18  stamp=2006-11  events=-
  doc_z_misc_navagraha/sUryadvAdashanAmastotra  stamp=2014-08  events=-
  doc_z_misc_shankara/shaktipITha  stamp=2012-05  events=-

first / same (7095):
  doc_devii/AryAmbikAshankarashAradAstotram  stamp=2018-11  events=a:2018-11
  doc_devii/bAlApanchAngam  stamp=2020-03  events=a:2020-03
  doc_ganesha/dhUmravarNabhaktipanchakastotramahaMkRRitaM  stamp=2024-06  events=a:2024-06
  doc_ganesha/gaNeshaprAtaHsmaraNaMsomakAntakRRitam  stamp=2024-04  events=a:2024-04
  doc_ganesha/shaktivinAyakastutiHsAvarNikRRitA  stamp=2024-06  events=a:2024-06
  doc_shiva/rAmalingAShTakam  stamp=2021-07  events=a:2021-07
  doc_shiva/shivArchanopadesham4  stamp=2024-06  events=a:2024-06
  doc_shiva/sundarakRRitashivastutyuparAntashivadarshavigrahavarNanam  stamp=2024-07  events=a:2024-07
  doc_shiva/umAnandabhairavastutiH  stamp=2026-06  events=a:2026-06
  doc_vishhnu/prahlAdakRRitashrInRRisiMhamantraH  stamp=2025-08  events=a:2025-08

first / earlier (1077):
  doc_devii/durga-a8  stamp=2022-09  events=u:2016-05,u:2022-09
  doc_devii/vAsavIkanyakAparameshvarIprArthanA2  stamp=2021-08  events=a:2019-06
  doc_ganesha/gakArAdigaNpatisahasranAmastotram  stamp=2025-05  events=a:2017-01
  doc_hanumaana/mantrAtmakammArutistotram  stamp=2022-12  events=a:2018-07,u:2022-12
  doc_shiva/AtmanAthasahasranAmAvalI  stamp=2017-02  events=a:2016-11,u:2017-02
  doc_shiva/ShoDaSharudrabIjAmRRitavandanA  stamp=2026-04  events=a:2024-10,u:2026-04
  doc_shiva/kirAtamUrtistotram  stamp=2021-07  events=a:2020-12
  doc_shiva/pAshupatasUtram  stamp=2025-09  events=a:2022-09
  doc_subrahmanya/kumAropaniShat  stamp=2024-02  events=a:2018-01,u:2019-11
  doc_vishhnu/nArAyaNastotram  stamp=2022-08  events=a:2021-08,u:2022-08

first / later_floor (119):
  doc_deities_misc/akkalakoTasvAmIbhajan2  stamp=2006-07  events=a:2010-10,u:2010-10
  doc_deities_misc/bhaavanaashtakam  stamp=2008-04  events=a:2010-10,u:2010-10
  doc_deities_misc/bhuutaadhipastotram  stamp=2008-04  events=a:2010-10,u:2010-10
  doc_devii/bAlAmbikAShTakam  stamp=2004-11  events=a:2010-10,u:2010-10
  doc_devii/bagalAmukhI108  stamp=2005-04  events=a:2010-10,u:2010-10,u:2017-05
  doc_devii/kaalikaasahasra  stamp=2004-04  events=a:2010-10,u:2010-10,u:2015-05,u:2015-05,u:2017-01,u:2017-01,u:2023-06
  doc_giitaa/suuryagiitaa  stamp=2008-10  events=a:2010-10,u:2010-10
  doc_shiva/amoghashivakavach  stamp=2005-10  events=a:2010-10,u:2010-10,u:2014-09,u:2015-11,u:2016-06
  doc_shiva/rudram  stamp=1998-07  events=u:2010-10,u:2011-06,u:2015-11,u:2017-05,u:2022-03,u:2022-07
  doc_upanishhat/brahma_upan  stamp=1996-04  events=a:2010-10,u:2010-10,u:2018-08

first / later_real (1039):
  doc_devii/bagalAmukhIhRidayam  stamp=2016-11  events=a:2017-07,u:2017-11
  doc_devii/lalitaa108naam  stamp=2000-11  events=u:2011-11,u:2024-03
  doc_devii/vidyAdAnavAksarasvatIhRidayastotra  stamp=2013-02  events=a:2013-09
  doc_ganesha/mayuureshvarastotram  stamp=2004-05  events=u:2024-04
  doc_shiva/shivakRRipArthaprArthanA  stamp=2024-01  events=a:2024-02
  doc_subrahmanya/murukAShTakam  stamp=2015-09  events=u:2016-06
  doc_veda/r03  stamp=2013-07  events=u:2017-11
  doc_veda/r04  stamp=2013-07  events=u:2017-11
  doc_vishhnu/viShNornAmastotramahAdevoktaNP  stamp=2013-06  events=a:2013-09
  doc_z_misc_general/bhAratimAmava  stamp=2019-09  events=a:2019-10

first / no_stamp (9):
  doc_deities_misc/suryanamaskArmantra  stamp=None  events=u:2021-01
  doc_devii/bhadrakAlIkavacham2  stamp=None  events=a:2020-09
  doc_devii/laxmi1000  stamp=None  events=u:2011-11,u:2011-11,a:2012-01,u:2012-01,u:2016-07
  doc_devii/sarasvatistotra  stamp=None  events=a:2013-12,u:2026-04
  doc_shiva/sharabhasahasranAmastotra  stamp=None  events=a:2017-08,u:2017-08,u:2020-08
  doc_shiva/shivamangalAShTaka  stamp=None  events=a:2011-08
  doc_veda/sangyaanasuukta  stamp=None  events=u:2014-12,u:2025-02
  doc_z_misc_shankara/ekashloki  stamp=None  events=-
  doc_z_misc_subhaashita/subhash  stamp=None  events=u:2016-07

updated only (1097):
  doc_deities_misc/keshavAdichaturviMshatinAmastotram  stamp=2022-03  events=u:2022-03
  doc_devii/raadhaakavach  stamp=2004-07  events=u:2026-06
  doc_giitaa/bgwordsSeqD  stamp=2021-08  events=u:2012-05,u:2014-12,u:2021-05
  doc_hanumaana/hanumatkavachaAnanda  stamp=2021-05  events=u:2016-06,u:2019-03,u:2021-01
  doc_shiva/AtmArpaNastuti  stamp=2021-08  events=u:2016-07,u:2017-01
  doc_shiva/munibhiHkRRitaMrudrastotram  stamp=2022-08  events=u:2022-08
  doc_shiva/vAsudevakRRitaMshivastotram  stamp=2025-11  events=u:2026-01
  doc_vishhnu/bhAvaprakAshAShTakam  stamp=2021-11  events=u:2021-11
  doc_vishhnu/chaturviMshatyavatArastotram  stamp=2015-05  events=u:2015-08,u:2015-10,u:2017-08
  doc_vishhnu/purIshvarAShTakam  stamp=2020-09  events=u:2020-09
```
