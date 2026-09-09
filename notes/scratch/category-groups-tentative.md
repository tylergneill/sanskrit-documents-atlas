# category tag groups — tentative, NOT IN USE

**Status (2026-08-12): rejected for now.** The filter UI ships with plain
normalized category strings in an autocomplete — no grouping. The buckets below
were judged too unreliable to act on: several assignments exist only to reach
zero-unsorted, and `venerated` never got a name.

Kept because the *evidence* is reusable if grouping is revisited: per-tag
frequency, location spread, and author-match rates, plus the spelling-fold list
at the foot. Every figure is computed from the Feb-2025 snapshot by
`scratchpad/emit_groups.py`; only the bucket assignments are hand judgment.

Columns: **freq** = documents carrying the tag; **locs** = how many of the 20
locations they span; **top** = share sitting in the single commonest location
(high = concentrated, low = spread); **auth** = share of tagged documents
actually *written by* that person, where the tag matches an `Author` value.

Totals: 332 raw tags, 214 of them not a listing slug.
Assigned below: 214. Unsorted: 0.


## author  (41 tags, 443 placements)

Tag names the **writer** of the tagged texts — author-match rate is high.
Safe to label *Author*.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `shrIdharasvAmI` | 124 | 10 | deities_misc 49% | 78/124 |
| `vedAnta-deshika` | 39 | 6 | vishhnu 46% | 24/39 |
| `vallabhaachaarya` | 28 | 4 | vishhnu 75% | 25/28 |
| `raghunAthadAsagosvAmin` | 27 | 4 | devii 59% |  |
| `chandrashekharabhAratI` | 19 | 5 | deities_misc 53% | 14/19 |
| `haridAsa` | 16 | 4 | vishhnu 62% | 16/16 |
| `abhinavagupta` | 15 | 5 | z_misc_major_works 40% | 14/15 |
| `vAlmIki` | 15 | 5 | raama 73% | 13/15 |
| `viThThaleshvara` | 14 | 3 | vishhnu 57% | 11/14 |
| `nIlakaNThadIkShita` | 13 | 5 | shiva 62% |  |
| `kShemendra` | 11 | 3 | giitaa 82% | 11/11 |
| `raghunAthajI` | 11 | 2 | vishhnu 91% | 9/11 |
| `sArvabhaumabhaTTAchArya` | 10 | 1 | deities_misc 100% | 10/10 |
| `tyAgarAja` | 9 | 2 | devii 89% | 9/9 |
| `jagannAthapaNDita` | 6 | 2 | z_misc_major_works 67% | 6/6 |
| `shrIkRiShNalIlAshukamuni` | 6 | 2 | vishhnu 83% | 5/6 |
| `bhartrihari` | 6 | 1 | z_misc_major_works 100% | 2/6 |
| `muttusvAmI-dIkShitAra` | 5 | 4 | devii 40% |  |
| `yogAnanda` | 5 | 2 | devii 60% | 3/5 |
| `pANinI` | 5 | 1 | z_misc_major_works 100% | 5/5 |
| `varAhamihira` | 5 | 1 | z_misc_sociology_astrology 100% | 4/5 |
| `rAmAnuja` | 4 | 2 | vishhnu 75% | 3/4 |
| `jagadIsha-shAstrI` | 4 | 1 | deities_misc 100% | 2/4 |
| `madhusUdanasarasvatI` | 4 | 1 | z_misc_major_works 100% | 3/4 |
| `jagaddharabhatta` | 4 | 2 | shiva 75% | 4/4 |
| `samartha-rAmadAsa` | 3 | 2 | raama 67% |  |
| `vidyAraNya` | 3 | 2 | z_misc_major_works 67% |  |
| `gauDapaada` | 3 | 2 | devii 67% | 1/3 |
| `kRiShNAnandasarasvatI` | 3 | 2 | devii 67% | 2/3 |
| `maheshvarAnandasarasvatI` | 3 | 2 | devii 67% | 1/3 |
| `puShpadanta` | 3 | 2 | shiva 67% | 1/3 |
| `chANakya` | 3 | 1 | z_misc_major_works 100% |  |
| `budhakauShika` | 3 | 1 | raama 100% | 3/3 |
| `vAngIpuram-narasinhAchArya` | 3 | 1 | vishhnu 100% | 3/3 |
| `jayadeva` | 2 | 2 | devii 50% | 2/2 |
| `parAsharabhaTTa` | 2 | 1 | vishhnu 100% | 2/2 |
| `yAmunAchArya` | 2 | 1 | vishhnu 100% | 2/2 |
| `purandaradAsa` | 2 | 1 | shiva 100% |  |
| `svAtitirunAL` | 1 | 1 | devii 100% | 1/1 |
| `parAshara` | 1 | 1 | devii 100% | 1/1 |
| `avadhUtasiddha` | 1 | 1 | z_misc_major_works 100% | 1/1 |

## venerated  (27 tags, 879 placements)

Tag names a person, but the texts are *about* or *addressed to* them
(stotras to a guru, works in a lineage) — author rate is low despite
high frequency. **Needs a name.** Not "author"; "figure" was rejected.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `vAsudevAnanda-sarasvatI` | 147 | 10 | deities_misc 33% | 8/147 |
| `sachchidAnanda-shivAbhinava-nRisiMhabhAratI` | 133 | 9 | devii 39% | 17/133 |
| `rAmakRiShNa` | 109 | 1 | deities_misc 100% |  |
| `vyAsa` | 77 | 10 | giitaa 23% | 18/77 |
| `puShpAshrIvatsan` | 69 | 9 | deities_misc 46% | 11/69 |
| `vAdirAja` | 58 | 6 | vishhnu 76% | 18/58 |
| `nimbArkAchArya` | 56 | 5 | deities_misc 50% | 3/56 |
| `rUpagosvAmin` | 44 | 3 | vishhnu 82% | 2/44 |
| `varadAnanda` | 27 | 4 | deities_misc 41% |  |
| `appayya-dIkShita` | 23 | 8 | shiva 52% | 1/23 |
| `ramaNa-maharShi` | 20 | 6 | deities_misc 55% |  |
| `shrIdhara-venkaTesha` | 20 | 5 | shiva 60% |  |
| `gaNapati-muni` | 18 | 7 | devii 44% | 3/18 |
| `brahmAnanda` | 18 | 5 | vishhnu 56% | 4/18 |
| `sadAshivabrahmendra` | 15 | 5 | z_misc_major_works 53% | 3/15 |
| `vivekAnanda` | 8 | 5 | z_misc_general 38% |  |
| `bhAgavatAnanda` | 6 | 3 | devii 50% |  |
| `Ananda-tIrtha` | 6 | 2 | vishhnu 67% | 0/6 |
| `dattAtreyAnandanAtha` | 5 | 2 | devii 80% | 1/5 |
| `ramana` | 4 | 1 | deities_misc 100% |  |
| `nRisiMhabhAratIsvAmi` | 4 | 3 | vishhnu 50% | 1/4 |
| `rangAvadhUta` | 3 | 2 | deities_misc 67% |  |
| `rAghavendra` | 3 | 2 | deities_misc 67% |  |
| `chandrashekharendrasarasvatI` | 3 | 3 | devii 33% |  |
| `tulasIdAsa` | 1 | 1 | giitaa 100% |  |
| `annamAchArya` | 1 | 1 | vishhnu 100% |  |
| `bhAratItIrtha` | 1 | 1 | vishhnu 100% |  |

## source_work  (42 tags, 667 placements)

Tag names the **text a passage was extracted from** — purāṇas, saṃhitās,
large works. A provenance axis, not a subject one.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `mudgalapurANa` | 125 | 5 | ganesha 91% |  |
| `brahmapurANa` | 52 | 6 | shiva 42% |  |
| `gaNeshapurANa` | 38 | 4 | ganesha 82% |  |
| `bRRihannAradIyapurANa` | 34 | 6 | vishhnu 53% |  |
| `brahmavaivartapurANa` | 29 | 5 | vishhnu 34% |  |
| `harivaMsha` | 28 | 3 | vishhnu 89% |  |
| `shivapurANa` | 27 | 5 | shiva 56% |  |
| `vAmanapurANa` | 26 | 4 | vishhnu 46% |  |
| `bhaviShyapurANa` | 25 | 5 | z_misc_navagraha 32% |  |
| `rigveda` | 25 | 3 | veda 92% | 1/25 |
| `panchadashI` | 24 | 4 | devii 83% |  |
| `viShNupurANa` | 23 | 4 | vishhnu 83% |  |
| `varAhapurANa` | 21 | 6 | vishhnu 52% |  |
| `garuDapurANa` | 19 | 6 | vishhnu 63% |  |
| `lingapurANa` | 19 | 2 | shiva 79% |  |
| `bRihaddharmapurANam` | 17 | 6 | devii 41% |  |
| `brahmANDapurANa` | 15 | 3 | devii 53% |  |
| `devibhagavatam` | 14 | 1 | purana 100% |  |
| `shrimadbhagavatam` | 14 | 1 | purana 100% |  |
| `matsyapurANa` | 13 | 5 | vishhnu 31% |  |
| `bRihatpArAshara` | 11 | 1 | z_misc_sociology_astrology 100% |  |
| `mArkaNDeyapurANa` | 10 | 2 | z_misc_navagraha 60% |  |
| `skandapurANa` | 10 | 6 | subrahmanya 30% |  |
| `saptashatI` | 7 | 1 | devii 100% |  |
| `saMhitA` | 7 | 5 | shiva 43% |  |
| `bhushuNDirAmAyaNam` | 5 | 1 | raama 100% |  |
| `agnipurANa` | 4 | 3 | vishhnu 50% |  |
| `bhAgavatapurANa` | 4 | 2 | vishhnu 75% |  |
| `narasiMhapurANa` | 4 | 2 | vishhnu 75% |  |
| `padmapurANa` | 3 | 2 | vishhnu 67% | 0/3 |
| `nAradapurANa` | 2 | 1 | vishhnu 100% |  |
| `linggapurANa` | 2 | 1 | shiva 100% |  |
| `nIlamatapurANa` | 1 | 1 | deities_misc 100% |  |
| `lakShmInArAyaNIyasaMhitA` | 1 | 1 | devii 100% |  |
| `bauddhastotrasangraha` | 1 | 1 | z_misc_major_works 100% |  |
| `viShNudharmopapurANa` | 1 | 1 | vishhnu 100% |  |
| `viShNudharmapurANa` | 1 | 1 | vishhnu 100% |  |
| `viShNudharmottarapurANa` | 1 | 1 | vishhnu 100% |  |
| `vAmapurANa` | 1 | 1 | vishhnu 100% |  |
| `bRihaddharmapurANa` | 1 | 1 | shiva 100% |  |
| `kUrmapurANa` | 1 | 1 | shiva 100% |  |
| `vAyupurANa` | 1 | 1 | shiva 100% |  |

## tradition  (14 tags, 1256 placements)

Tag names a **sectarian or textual tradition**. `shivarahasya` is the
clearest case: 728 documents, almost all in one location.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `shivarahasya` | 728 | 6 | shiva 97% |  |
| `rAmAnanda` | 120 | 7 | raama 55% |  |
| `puShTimArgIya` | 118 | 5 | vishhnu 70% |  |
| `svAminArAyaNa` | 51 | 4 | vishhnu 76% |  |
| `jaina` | 45 | 3 | devii 49% |  |
| `stavamAlA` | 43 | 3 | vishhnu 81% |  |
| `rAmAnujasampradAya` | 35 | 4 | vishhnu 40% |  |
| `kAshmIrashaivadarshanam` | 29 | 5 | shiva 62% |  |
| `stavAvalI` | 27 | 4 | devii 59% |  |
| `stavAmRRitalaharI` | 26 | 3 | vishhnu 65% |  |
| `vIrashaiva` | 24 | 3 | shiva 92% |  |
| `shaktipITha` | 8 | 4 | devii 62% |  |
| `Natha-Sampradaya` | 1 | 1 | giitaa 100% |  |
| `kAshimIrashaivadarshanam` | 1 | 1 | shiva 100% |  |

## verse_form  (34 tags, 873 placements)

Tag names the **shape of the text** — usually a verse count. Same kind as
`aShTaka`, which *is* a listing page, so this bucket is a real facet.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `nAmAvalI` | 437 | 11 | devii 32% |  |
| `dvAdasha` | 64 | 9 | ganesha 23% |  |
| `dashaka` | 60 | 8 | deities_misc 27% |  |
| `nava` | 56 | 11 | devii 32% |  |
| `viMshati` | 49 | 10 | vishhnu 24% |  |
| `ShoDasha` | 28 | 5 | devii 36% |  |
| `panjara` | 23 | 7 | vishhnu 43% |  |
| `shatI` | 23 | 5 | devii 70% |  |
| `sangraha` | 21 | 7 | z_misc_subhaashita 29% |  |
| `daNDaka` | 19 | 7 | devii 32% |  |
| `chatuHshlokI` | 15 | 3 | vishhnu 47% |  |
| `chaturviMshati` | 12 | 6 | vishhnu 50% |  |
| `saptaka` | 11 | 5 | devii 27% |  |
| `ekAdasha` | 10 | 1 | ganesha 100% |  |
| `ShaTpadI` | 8 | 6 | z_misc_general 25% |  |
| `panchAshata` | 6 | 4 | deities_misc 33% |  |
| `ShaTka` | 5 | 2 | deities_misc 60% |  |
| `panchashatI` | 4 | 2 | devii 75% |  |
| `dvishatI` | 3 | 3 | deities_misc 33% |  |
| `pancha` | 2 | 2 | devii 50% |  |
| `shati` | 2 | 1 | ganesha 100% |  |
| `aShTAdasha` | 2 | 2 | vishhnu 50% |  |
| `triMshikA` | 2 | 1 | shiva 100% |  |
| `trikam` | 1 | 1 | devii 100% |  |
| `panchAshat` | 1 | 1 | ganesha 100% |  |
| `panchAshatnAmAvalI` | 1 | 1 | ganesha 100% |  |
| `dvAdhasha` | 1 | 1 | ganesha 100% |  |
| `astra` | 1 | 1 | hanumaana 100% |  |
| `nAMAvalI` | 1 | 1 | z_misc_general 100% |  |
| `panchAshatanAmAvalI` | 1 | 1 | subrahmanya 100% |  |
| `AyutanAmAvalI` | 1 | 1 | shiva 100% |  |
| `ShaShTi` | 1 | 1 | shiva 100% |  |
| `mahimna` | 1 | 1 | shiva 100% |  |
| `vedapAda` | 1 | 1 | shiva 100% |  |

## genre  (20 tags, 1151 placements)

Tag names **what kind of thing the text is** — a praise-poem, an
instruction, a commentary.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `stuti` | 450 | 10 | shiva 49% |  |
| `upadesha` | 167 | 10 | shiva 71% |  |
| `mangala` | 132 | 11 | vishhnu 27% |  |
| `dhyAnam` | 100 | 9 | devii 35% |  |
| `tIrthakShetra` | 66 | 5 | shiva 65% |  |
| `stava` | 59 | 9 | shiva 37% |  |
| `article` | 33 | 3 | z_misc_general 91% |  |
| `prapatti` | 29 | 5 | vishhnu 31% |  |
| `bIjAdyAkSharamantrAtmaka` | 27 | 8 | hanumaana 26% |  |
| `mAhAtmya` | 25 | 7 | devii 36% |  |
| `gadyam` | 22 | 6 | deities_misc 45% |  |
| `chAlisA` | 8 | 3 | devii 50% |  |
| `bAlakavitA` | 6 | 2 | z_misc_general 67% |  |
| `sUchI` | 6 | 3 | z_misc_major_works 67% |  |
| `bhAShya` | 5 | 2 | z_misc_major_works 60% |  |
| `vyAkhyA` | 4 | 2 | upanishhat 75% |  |
| `apAmArjana` | 4 | 1 | vishhnu 100% |  |
| `dhyAna` | 3 | 3 | devii 33% |  |
| `kAvya` | 3 | 2 | z_misc_general 67% |  |
| `kathA` | 2 | 1 | z_misc_general 100% |  |

## encoder  (15 tags, 314 placements)

Tag names the **person who typed the text up**, not its author. Arguably
not about the text at all — candidate for dropping from the filter.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `pradIptakumArananda` | 78 | 7 | z_misc_general 49% |  |
| `hkmeher` | 41 | 5 | devii 44% |  |
| `bharata` | 34 | 1 | z_misc_major_works 100% |  |
| `moropanta` | 32 | 7 | vishhnu 41% |  |
| `paNDita-bellaMkoNDa-rAmarAya-kavIndra` | 20 | 1 | vishhnu 100% |  |
| `vAsudevanElayath` | 19 | 5 | deities_misc 26% |  |
| `jagannatha` | 16 | 1 | vishhnu 100% |  |
| `ApaTIkara` | 15 | 8 | devii 33% |  |
| `vishvanAthachakravartin` | 15 | 3 | vishhnu 73% |  |
| `vishvanAthachakravartina` | 12 | 2 | vishhnu 58% |  |
| `koriDevishvanAthasharmA` | 12 | 4 | vishhnu 50% |  |
| `vrajakishora` | 8 | 4 | vishhnu 38% |  |
| `kRiShNarAya` | 7 | 1 | vishhnu 100% |  |
| `moropant` | 4 | 3 | shiva 50% |  |
| `rAjendrabhAve` | 1 | 1 | z_misc_general 100% |  |

## language  (7 tags, 692 placements)

Tag names a **language or register** other than plain Sanskrit.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `sanskritgeet` | 519 | 9 | z_misc_general 87% |  |
| `svara` | 151 | 13 | veda 47% |  |
| `hindi` | 15 | 6 | shiva 33% |  |
| `marAThI` | 3 | 2 | z_misc_general 67% |  |
| `learnsanskrit` | 2 | 1 | z_misc_major_works 100% |  |
| `hindI` | 1 | 1 | deities_misc 100% |  |
| `general` | 1 | 1 | z_misc_general 100% |  |

## deity_figure  (14 tags, 140 placements)

Tag names a **deity or figure the text concerns** that has no listing page
of its own.

| tag | freq | locs | top | auth |
|---|---:|---:|---:|---:|
| `sItA` | 47 | 4 | devii 74% |  |
| `sociology_astrology` | 27 | 1 | z_misc_sociology_astrology 100% |  |
| `narayana` | 19 | 4 | vishhnu 74% | 0/19 |
| `shAkambharI` | 7 | 1 | devii 100% |  |
| `annapUrNA` | 6 | 2 | devii 83% |  |
| `yoginI` | 6 | 1 | devii 100% |  |
| `annapUrNa` | 5 | 1 | devii 100% |  |
| `brahma` | 4 | 2 | deities_misc 75% | 0/4 |
| `agastya` | 4 | 2 | devii 75% | 0/4 |
| `buddha` | 4 | 3 | vishhnu 50% |  |
| `hari` | 4 | 1 | vishhnu 100% |  |
| `shArikA` | 3 | 1 | devii 100% |  |
| `shani` | 3 | 1 | z_misc_navagraha 100% |  |
| `yogini` | 1 | 1 | devii 100% |  |

## spelling variants to fold — APPLIED 2026-08-13

**Done; kept as the record of what was folded and why.** All 12 are now in
effect, though only 4 needed a new or corrected `ALIASES` entry: 4 of them
already merged mechanically (`hindi`, `annapUrNA`, `yoginI`, `shatI` — the
vowel-folding rule reaches them), 5 were already correct, 3 were **backwards**
(merging to the minority spelling), and 1 was missing.

Applying them exposed a larger bug: `build_key` was only ever called for
`--report` statistics, so `parse_snapshot` stored raw spellings and *no* alias
had ever affected the data. Normalization now runs in `collect`. Result:
332 raw spellings → **284 concepts**, 87/87 slug round-trip intact.

The surviving spelling is the slug where one exists, else the majority — the
three backwards entries had `dhyAna` (3 documents) beating `dhyAnam` (100).

```
hindi (15)  <-  hindI (1)
annapUrNA (6)  <-  annapUrNa (5)
yoginI (6)  <-  yogini (1)
dhyAnam (100)  <-  dhyAna (3)
vishvanAthachakravartin (15)  <-  vishvanAthachakravartina (12)
moropanta (32)  <-  moropant (4)
ramaNa-maharShi (20)  <-  ramana (4)
panchAshata (6)  <-  panchAshat (1)
lingapurANa (19)  <-  linggapurANa (2)
shatI (23)  <-  shati (2)
bRihaddharmapurANam (17)  <-  bRihaddharmapurANa (1)
panchaka (157)  <-  pancha (2)
```
