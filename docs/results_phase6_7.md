# Phase 6–7 Results and Validation

**Run date:** 2026-10-18. Data were downloaded the same day; manifests with SHA-256 checksums are in `data/raw/*/<stamp>/manifest.json`. `data/raw` and `data/processed` are git-ignored; every result can be regenerated with the commands in §8.

**Read this first.** All findings are **descriptive**.
- Load, capacity and consumption figures are **published statistics**.
- Every generation figure is **modelled**: NASA POWER weather run through pvlib, or a generic wind power curve. None is measured plant output.
- Peak **months** are observed. Peak **hours** are scenario windows.
- No result here is an ELCC, a reserve margin or a reliability metric.

---

## 1. What the data actually contain (Phase 1 gate, resolved)

| Dataset | Verified content | Licence (portal) |
|---|---|---|
| D2 monthly load by region | 1,584 rows = 132 months (2009-01 → 2019-12) × 4 areas × {max, avg, min}, GW | not stated |
| D3 "installed capacity (peak load) by region 2014" | **Actually 2005–2019**: peak load, installed capacity (2005–2019), available capacity (2010–2019), 4 areas, GW | Public Domain |
| Consumption by sector & region | 2005–**2025**, 4 areas, MWh | Public Domain |
| D1 regional statistics 1992–2009 | 5 regions (incl. Northern), 6 indicators | Public Domain |
| D7 renewables by project | 68 records, **province + city, no coordinates**, status only Installed/Planned, last modified 2024-04-03 | Public Domain |
| GEM wiki (102 projects, 108 phases) | status, commissioning year, capacity, WGS84 coordinates (59 exact, 49 approximate) | CC BY-NC-SA |
| Natural Earth admin-1 | 13 Saudi provinces (ISO 3166-2) | Public domain |
| NASA POWER hourly | 2019–2023 at 100 project coordinates, 0 missing hours | open (attribution) |

**Gate passed:** D2 has the four operating areas, and 99.8–100% of capacity can be placed in a province.

## 2. Data-quality findings (part of the contribution, G7)

1. **D2 label swap, Central 2011:** in all 12 months the value labelled "Minimum" is the largest. Corrected by sorting under a documented rule (`src/cleaning.py`, logged in `results/tables/d2_corrections_log.csv`).
2. **Three isolated inconsistent months** (Eastern 2015-10, 2015-12, 2019-10): the maximum is set to NaN in the main run, with a sensitivity file that keeps the raw values.
3. **Duplicated years:** 2010 is an exact copy of 2009 in every area and measure, and 2018 is an exact copy of 2017 for Eastern and Southern (`d2_duplicate_years.csv`). Duplicated years are excluded from year-specific statistics and counted once in pooled statistics.
4. **Suspected outlier:** Central 2017-02, max 17.9 GW against an average of 8.7 GW. It is retained and flagged (`d2_anomalies_max_to_avg.csv`).
5. **KAPSARC project table:** 68 records collapse to **28 distinct projects** (alias table `data/manual/kapsarc_project_aliases.csv`). Summing all records gives 49.8 GW against **22.3 GW** of distinct projects, an overcount of 2.2×. Three rows are unlocated aggregates (14.4 GW). Three projects carry conflicting provinces (Ar Rass, Layla, Saad). Only 0.7 GW is marked installed, against **12.0 GW operating in GEM**. This table should not be used as a current fleet without de-duplication.

## 3. RQ1: regional demand, peak and capacity

| Area | Peak 2005 → 2019 (GW) | Peak CAGR 2005–19 | Peak CAGR 2015–19 | Installed/peak 2019 | Consumption CAGR 2019–25 | Share of 2025 consumption |
|---|---|---|---|---|---|---|
| Central | 9.1 → 20.0 | 5.8% | −0.4% | **0.82** | 4.9% | 31% |
| Eastern | 9.3 → 19.0 | 5.3% | −1.2% | 1.65 | 3.7% | 29% |
| Southern | 2.2 → 6.0 | 7.5% | +3.2% | 1.12 | 4.2% | 10% |
| Western | 8.6 → 17.0 | 5.0% | −2.2% | 1.80 | 4.1% | 30% |

- **Central is the only area whose installed capacity was below its own peak** in 2019, by 3.5 GW. It relies on transfers from other areas. This is descriptive only, not a reserve margin.
- Peaks grew about 5–7.5% a year until 2015, then plateaued from 2015 to 2019. Consumption growth resumed at 3.7–4.9% a year from 2019 to 2025. There are no regional peak data after 2019.
- **H1 is supported.** The annual peak falls in Jul–Aug in every area: the mode is July for Central and Southern and August for Eastern and Western. Months within 5% of the annual peak are May–Sep in Central and Western and Jun–Sep in Eastern and Southern. The median summer/winter ratio differs: Central 1.67, Western 1.70, Eastern 1.49, Southern 1.31. With 7–9 independent years per area, no formal test was run.
- **V2:** the sum of the four regional peaks equals the national peak to within 0–4% every year from 2005 to 2019. The regional peaks are therefore close to simultaneous, so a renewable fleet cannot rely on regional peak diversity.

## 4. RQ2: geography of capacity vs peak (`rq2_*`, Fig. 2)

Base mapping, dissimilarity D against the 2019 peak shares (Central 32%, Eastern 31%, Southern 10%, Western 27%):

| GEM fleet | GW | D (base) | D range, 36 mappings | Mappings with D > 0.2 |
|---|---|---|---|---|
| Operating | 12.0 | 0.23 | 0.11–0.29 | 67% |
| Operating + construction | 21.8 | 0.31 | 0.28–0.38 | **100%** |
| Full pipeline | 54.0 | 0.20 | 0.16–0.28 | 89% |

- **Southern has no operating or under-construction capacity** in GEM, against about 10% of peak. Its share of the full pipeline is 11%.
- **Western dominates capacity under construction** (55–65% of operating + construction, against 27% of peak). **Eastern is under-represented in every set** (3–29% of capacity, against 31% of peak).
- **H2 is partly supported.** D > 0.2 holds in every mapping only for the operating + construction set. For the operating fleet the result depends on how Hail, Al-Jouf and the Northern Borders are assigned. D against 2025 consumption gives the same picture (base: 0.22, 0.29, 0.18).
- The KAPSARC (de-duplicated) full pipeline spans D = 0.10–0.31 across mappings and province conflicts. That is a wider range than GEM, which reflects source uncertainty.

## 5. RQ3: modelled peak-season contribution (`rq3_*`, Figs. 3–4)

Median PV capacity factor in each area's observed peak months, full GEM pipeline, over 5 weather years × 36 mappings:

| Window (local time) | 12–15 | 14–17 | 16–19 | 19–22 | All hours |
|---|---|---|---|---|---|
| Tracker | 0.72–0.81 | 0.51–0.65 | 0.18–0.30 | **0.00** | 0.27–0.31 |
| Fixed | 0.69–0.77 | 0.44–0.54 | 0.14–0.20 | **0.00** | 0.23–0.26 |

(Ranges are across the four areas.)

- **The window, not the nameplate, dominates.** The same fleet contributes about 0.8 of nameplate if the peak falls at 12–15 h and nothing at 19–22 h. The hour of the regional peak is therefore the decisive unknown, and no public data pin it down.
- **H3, first part, is supported for fixed-tilt PV in all scenarios.** With trackers it holds for Central and Southern, but in some scenarios the 16–19 h value exceeds the all-hours mean in Eastern and Western.
- **H3, second part (Western above Eastern at 16–19 h), is weakly supported.** The median difference is +0.04. The direction holds in 67% of tracker scenarios and 91% of fixed.
- **Mounting matters as much as location:** trackers add 0.04–0.12 over fixed tilt at 14–17 h and 16–19 h, depending on the area. Mounting per project is not known.
- **Wind is evening-weighted.** Its median capacity factor at 19–22 h is 0.22–0.36, its highest window. But only 0.4 GW of wind is operating (11 GW in the pipeline).
- **Losses and temperature-coefficient sensitivity** (10%/−0.30 to 20%/−0.45 %/K) move the 16–19 h tracker value from 0.23 to 0.28, smaller than the window effect.
- **Storage (illustrative):** in peak months, midday PV always fills the battery, so the 19–22 h firm fraction is set by battery energy alone. For example, 0.5 kW × 4 h per kW of PV holds 0.50 of nameplate, and 1 kW × 2 h holds 0.55. Charging is never the constraint at the current fleet size. This is arithmetic, not a dispatch study.

## 6. Validation (Phase 7)

| Check | Result | Reading |
|---|---|---|
| V1 D2 annual max vs D3 regional peak | median \|diff\| 3.7%; 68% of region-years within 5% | Two KAPSARC tables agree reasonably; both are ECRA-derived, so they are not independent |
| V2 Σ regional peaks vs national peak (GASTAT) | ratio 0.97–1.04 | Regional peaks are consistent with the national series |
| V3 modelled PV annual CF | 0.19–0.30, none outside 0.18–0.33 | Plausible. **Not validated against any Saudi plant output**, because none was found |
| Weather completeness | 0 missing hours in 100 × 43,824 | — |

Claims checked against the Phase 7 questions:
- Every number above comes from a logged transformation.
- Regional figures carry mapping ranges.
- Generation is labelled modelled.
- No figure is described as reliability.

## 7. RQ4: what each resolution can and cannot establish

| Claim | Annual public data | Monthly public data (D2) | Needs hourly data |
|---|---|---|---|
| Regional demand and peak growth | ✔ (D3, consumption to 2025) | ✔ | — |
| Regional capacity vs own peak (Central deficit) | ✔ descriptive | — | adequacy: ✘ |
| Geography of RE vs peak (D index) | ✔ | — | — |
| Which months matter | ✘ | ✔ | — |
| RE output in peak months | — | ✔ (modelled) | — |
| RE output at the peak hour | ✘ | ✘ (bounded by scenario windows only) | ✔ |
| Capacity credit / ELCC / reserve margin | ✘ | ✘ | ✔ plus outage data |
| Storage needed for the evening peak | ✘ | illustrative bound | ✔ |

## 8. Reproduce

```bash
pip install -r requirements.txt
python -m src.data_ingestion
python -m src.data_validation data/raw/kapsarc/*/*/
python -m scripts.build_processed     # D2/D3/consumption tables, corrections log, Natural Earth provinces
python -m scripts.fetch_gem_wiki
python -m scripts.build_projects
python -m scripts.run_rq1
python -m scripts.run_rq2
python -m scripts.run_rq3
python -m scripts.run_storage_validation
python -m scripts.make_figures
```

## 9. Limitations specific to these results
- Regional peaks end in 2019, while the fleet assessed is 2026. The comparison is with the last observed structure.
- GEM's "operating" set includes 47 "Assumed PV" entries, many of them unnamed regional farms. Its statuses are GEM's and do not come from SPPC.
- Capacity units are mixed (65 MWac, 35 MW, 8 MWp) and used as reported.
- NASA POWER is coarse (about 0.5°) satellite/reanalysis data. Dust events and soiling are only partly represented.
- The province-to-operating-area mapping is still unverified, which is why every result carries 36 scenarios.
