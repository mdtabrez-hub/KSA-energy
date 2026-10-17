# Phases 3–5: Research Direction, Questions, Hypotheses and Methodology

**Date:** 2026-10-17
**Basis:** the Phase 1–2 report (`docs/phase1_2_audit_and_gap_report.md`), worked with the evidence available so far. No KAPSARC file has been downloaded yet. Everything below is a **design**; the only computed numbers are the clear-sky geometry illustration in §6, which is labelled as such.

---

## 1. Phase 3: direction selection

### 1.1 Candidates

- **A. Resolution-aware assessment of the renewable fleet's regional peak-season contribution.** Where the actual projects are, how their modelled output lines up with each operating area's *observed* monthly peak structure and with *assumed* peak hours, and which adequacy claims remain unidentifiable without hourly data.
- **B. Climate sensitivity of regional monthly peak load (2009–2019).** Regress monthly maximum load by operating area on reanalysis temperature.
- **C. Reconciliation of Saudi renewable-project databases.** Compare KAPSARC, GEM and Ministry/SPPC records, and quantify how much regional indicators depend on which source is used.

### 1.2 Scores (1–5, unweighted, with the evidence behind each)

| Criterion | A | B | C | Evidence |
|---|---|---|---|---|
| Novelty (public literature) | 3 | 2 | 2 | No public study compares the actual fleet with regional peak structure (S12). Utility work exists (L12). B overlaps L05, L30 and L31. C is data curation. |
| Evidence of a genuine gap | 3 | 2 | 3 | Firm-capacity assumptions drive CEM results (L28). Regional climate sensitivity already studied for energy (L05). Database disagreement observed (W03). |
| Data accessibility | 3 | 4 | 4 | A needs D2, D7 and weather. B needs D2 and weather. C needs D7 and GEM. |
| Data quality | 2 | 3 | 3 | D2 ends 2019. D7's location field is unverified. |
| Methodological feasibility | 4 | 4 | 5 | Transparent metrics and pvlib. No optimisation is required. |
| Electrical-engineering relevance | 5 | 3 | 2 | A addresses peak adequacy inputs directly. |
| Ability to validate | 2 | 4 | 4 | A has no Saudi plant output to validate against, only benchmark capacity factors. B and C validate internally. |
| Reproducibility | 5 | 5 | 5 | Public data and code. |
| Practical significance | 4 | 3 | 3 | Planning inputs and storage siting. |
| Journal suitability (EE/energy) | 4 | 3 | 2 | |
| **Total (of 50)** | **35** | **33** | **33** | The totals are close, so the decision rests on the reasons in §1.3, not the arithmetic. |

### 1.3 Decision

**Preferred direction: A, with C as a built-in robustness layer and B as a supporting analysis inside A.**

- **Decisive reason:** only A addresses the input that Saudi planning models currently *assume*, namely how much nameplate renewable capacity is available when each region's load peaks (L28). A can be done honestly at the resolution public data allow, provided the study is framed around that resolution limit.
- **Exact gap:** within the reviewed public literature, no study evaluates the *actual* (installed and pipeline) Saudi solar and wind fleet against *observed* regional peak-load structure, or states which peak-contribution claims monthly public data can and cannot support.
- **Strongest expected contribution:** a reproducible, resolution-aware bounding framework, with location-specific peak-window capacity-factor ranges for the real fleet by operating area, propagated through region-mapping, status and weather uncertainty.
- **Most important feasibility risk:** the 2019 end of regional peak data versus a fleet built from 2021 onward, compounded by an unverified region mapping.
- **Original direction:** **narrowed**. "Peak-load requirements" becomes observed monthly peak structure plus scenario peak hours. RQ3 is reframed, RQ4 becomes a sensitivity, and emissions are dropped.

---

## 2. Phase 4: final research questions

**Working title:** *What Public Data Can and Cannot Show: A Resolution-Aware Assessment of Saudi Arabia's Solar and Wind Fleet against Regional Peak-Load Structure*

**Alternatives:**
1. *Beyond Nameplate: Bounding the Peak-Season Contribution of Saudi Renewable Projects by Operating Area with Public Data*
2. *Regional Alignment of Saudi Renewable Deployment with Seasonal Peak Load: A Reproducible Public-Data Assessment*

**Aim:** quantify, with stated uncertainty and resolution limits, how the geography and modelled timing of Saudi solar and wind projects align with each operating area's observed peak-load structure.

| RQ | Question | Data | Status of the original RQ |
|---|---|---|---|
| RQ1 | How did monthly peak load, its seasonality and the load factor evolve by operating area in 2009–2019? | D2 (+ D1, D4 for context) | Narrowed version of original RQ1 (capacity series dropped: none after 2014) |
| RQ2 | How does the regional distribution of installed and pipeline RE capacity compare with the regional distribution of peak load and energy demand, and how sensitive is this to region mapping and project status? | D7 + GEM; D2 (2019); X1 (2023 energy) | Original RQ2, with uncertainty made explicit |
| RQ3 | What fraction of nameplate capacity does the fleet's *modelled* output provide, by operating area, during (a) each area's *observed* peak months and (b) *assumed* peak-hour windows, and how wide are these bounds? | D7 coordinates, weather (NASA POWER/ERA5), D2 peak months, scenario windows | Original RQ3 reframed; no ELCC and no observed coincidence |
| RQ4 | Which adequacy-related claims are identifiable from annual, monthly and hourly public data respectively? | Synthesis of RQ1–RQ3 | New (replaces storage RQ). Storage enters only as a sensitivity: hours of storage needed to shift output into a stated evening window. |

---

## 3. Hypotheses

All hypotheses are **descriptive**. None is causal.

| H | Statement | Variables and operational definition | Test | Cannot be tested if | Main confounders and caveats |
|---|---|---|---|---|---|
| H1 | Annual peaks fall in Jun–Sep in every operating area, but the summer/winter peak ratio differs between areas. | `peak_month`, `summer_winter_ratio` from D2 (`src.metrics.monthly_peak_structure`) | Descriptive counts; Kruskal–Wallis on yearly ratios across areas (n ≈ 11 years per area, low power, reported as such) | D2 is national, or has fewer than 4 regions | Reclassification of areas, data revisions, 2016–2018 tariff reforms |
| H2 | The regional distribution of RE capacity differs materially from the distribution of peak load: dissimilarity index D > 0.2 under the base mapping *and* across all 36 mapping scenarios. | D = ½ Σ\|s_cap − s_peak\| (`dissimilarity_index`). Capacity by status class; peak = 2019 regional annual maximum. | Distribution of D across mapping × status × source scenarios. The 0.2 threshold is a pre-registered descriptive cut-off, not a significance test. | D7 location unusable *and* GEM coordinates unavailable | Temporal mismatch (2019 load vs 2026 fleet); transmission makes local mismatch partly irrelevant, so D is geography, not adequacy |
| H3 | Under any assumed peak window ending after 17:00 local time, the fleet's modelled capacity factor in that window is below its daily mean in the peak month, and this gap is larger for eastern sites than western sites because of solar-time offset under a single clock. | A[r, T] = mean per-kW output over T (`peak_window_capacity_factor`). Site longitude. | Capacity-weighted A by area across windows, mounting (tracker/fixed), weather years | No coordinates | Tracker share unknown, so both mountings are bounded; dust/soiling missing from model inputs; heat derating |
| H4 | Conclusions about H2–H3 that hold at monthly resolution are a strict subset of those claimed in capacity-to-peak ratio studies. | Claim-by-resolution matrix (RQ4) | Logical/identification analysis, not statistics | n/a | — |

No direction is hypothesised for wind coincidence. The wind share is small and the resource timing is site-specific.

---

## 4. Phase 5: methodology

### 4.1 Data integration
1. Ingest D2, D7, D1, D4, X1 and GEM via `src/data_ingestion.py`. Raw files stay immutable with SHA-256 manifests.
2. Audit each with `src/data_validation.py`: row count vs portal metadata, fields, missing values, duplicates, region labels.
3. **Snapshot rule:** all project records are frozen at one download date. Status classes are kept separate (installed / under construction / awarded / tendered / planned) and are never summed across classes without labelling.
4. **De-duplication of KAPSARC × GEM:** match on normalised name, capacity (±5%) and distance (< 25 km). Unmatched records are reported, never silently merged.

### 4.2 Geography
- Coordinates are taken from D7 if they are numeric points, otherwise from GEM (exact-flagged first), otherwise the city centroid, with an accuracy flag carried into every result.
- Assign the administrative region by point-in-polygon. The boundary source is to be chosen; candidates are GADM or geoBoundaries (licence to check), in CRS EPSG:4326.
- Administrative region → operating area via `config/region_mapping.yaml`. The base mapping is **unverified**. All 36 combinations of the ambiguous regions (Hail, Al-Jouf, Northern Borders, Al-Baha) are evaluated by `src.region_mapping.scenarios()`, and results are reported as ranges.
- Projects within 25 km of a regional boundary are flagged and re-run with the neighbouring assignment.

### 4.3 Demand-side indicators (RQ1)
For area r and year t, using the definitions in `src/metrics.py`:

- annual peak P[r,t] = max over months of monthly maximum load
- growth gP[r,t] = 100 (P[r,t]/P[r,t−1] − 1); CAGR over 2009–2019
- load factor LF[r,t] = mean(monthly average load) / P[r,t]
- peak month and summer/winter ratio

Supporting analysis B: OLS of monthly maximum load on area-weighted monthly maximum temperature (ERA5 or NASA POWER), with month and year fixed effects and HAC (Newey–West) errors. Residual autocorrelation is reported. The analysis is descriptive, with no causal claim.

### 4.4 Supply-side modelling (RQ3)
- Per-kW AC output per project from `src/renewable_model.py`: pvlib solar position; single-axis tracker (±60°, backtracking, GCR 0.35) **or** fixed tilt = latitude, with both reported because mounting per project is unverified; PVsyst cell temperature; PVWatts DC with γ = −0.35 %/K; 14% lumped losses; DC/AC ratio 1.25.
- **Weather:** NASA POWER hourly (or ERA5) for at least 5 weather years at each project coordinate. Clear-sky output is used *only* for the geometry illustration (§6).
- **Wind:** windpowerlib with a generic 4–5 MW power curve and hub-height extrapolation (power law, α from site data). Reported separately and labelled modelled.
- **Validation:** there is no Saudi plant output to compare against, so annual modelled capacity factors are compared with published annual capacity factors where official figures exist (e.g. annual generation reported for a commissioned plant). Any such figure must be sourced before use. Otherwise validation is limited to sensitivity analysis.

### 4.5 Peak-contribution bounds (RQ3)
- **Observed component:** months M_peak[r] = the months in which area r's monthly maximum is within 5% of its annual maximum in 2017–2019 (from D2).
- **Scenario component:** windows T ∈ {12–15, 14–17, 16–19, 19–22 local}, each reported separately. None is claimed to be the true peak hour.
- **Metric:** A[r, T, M] = capacity-weighted mean per-kW output over hours in T during M_peak[r]. It is reported as a range over weather years × mounting × mapping × status × database.
- **Not computed:** ELCC, LOLE and reserve margin. The reasons (no hourly load, no outage data) are stated in the paper.

### 4.6 Storage sensitivity
For each area and window, E_shift = the hours of storage at rated power needed to move modelled midday output into the window, assuming 85% round-trip efficiency, SoC between 10% and 100%, daily cycling, no grid charging, and no simultaneous charge and discharge. This is an illustrative sizing bound, not an optimisation.

### 4.7 Uncertainty
| Type | Source | Treatment |
|---|---|---|
| Data | status classes, database choice, coordinate accuracy | Scenario enumeration; KAPSARC vs GEM vs union |
| Classification | admin region → operating area | 36 mapping scenarios |
| Model | mounting, losses, temperature coefficient, wind power curve | Both mountings; losses 10–20%; γ −0.30 to −0.45 %/K |
| Weather | inter-annual variability | ≥ 5 weather years |
| Scenario | peak windows | four windows, each reported separately |

Results are reported as min–median–max with no more than two significant figures.

---

## 5. Figures and tables (planned; none produced from real data yet)
1. Monthly maximum load by operating area, 2009–2019 (small multiples), with peak months marked (D2).
2. Map of RE projects by status class over administrative and operating-area boundaries (D7 + GEM).
3. Capacity share vs peak share by area, with whiskers across mapping scenarios (H2).
4. A[r, T] heat-map by area × window, tracker vs fixed (H3).
5. Distribution of the dissimilarity index across scenarios.
6. Claim-by-resolution matrix (RQ4).
7. Supplementary: solar noon and clear-sky window capacity factor by longitude (§6).

---

## 6. Data-free illustration: solar timing under one national clock

Saudi Arabia spans about 34.5°E–55.7°E but uses one clock (UTC+3, with no daylight saving), so solar noon is not at the same clock time everywhere. This can be computed exactly from solar geometry, with no external data. `scripts/solar_timing_demo.py` produces `results/tables/solar_timing_clearsky.csv`.

**What the table is:** clear-sky (Ineichen, bundled Linke turbidity) per-kW AC output for July 2023, an assumed 40 °C air temperature, and the model settings in §4.4, at two GEM-"exact" project coordinates, two GEM-"approximate" ones and four city load centres. **What it is not:** an estimate of any plant's real output. There is no dust, cloud, soiling or curtailment, and the windows are scenarios.

| Site | Solar noon, 21 Jul (UTC+3) | Tracker CF 14–17 | Tracker CF 16–19 | Fixed CF 16–19 | CF 19–22 |
|---|---|---|---|---|---|
| Dammam (Eastern) | 11:46 | 0.66 | 0.30 | 0.15 | 0.00 |
| Riyadh (Central) | 11:59 | 0.74 | 0.39 | 0.20 | 0.00 |
| Sudair PV (GEM exact) | 12:04 | 0.74 | 0.41 | 0.21 | 0.00 |
| Jeddah (Western) | 12:29 | 0.79 | 0.53 | 0.29 | 0.00 |
| Tabuk I PV (GEM exact) | 12:45 | 0.80 | 0.61 | 0.34 | ≤ 0.01 |

Reading, within its limits:
- Solar noon spans about **1 hour** of clock time across these sites. Under clear skies, a 16–19 window captures roughly twice the per-kW output at Tabuk that it does at Dammam. This is what H3 tests with real weather.
- Mounting matters as much as location for late-afternoon output: the tracker gives about twice the fixed-tilt 16–19 value at the same site. Mounting per project is therefore a first-order uncertainty to resolve.
- Any peak that extends past 19:00 receives essentially nothing from PV, so storage or other resources determine it.
- The Dammam values are also lower at midday. That reflects the higher Linke turbidity in pvlib's climatology there, not a site measurement.

---

## 7. Limitations (known before any analysis)
- Regional peak data end in 2019, while the fleet assessed is 2021 onward. The comparison is with the most recent observed structure, not with contemporaneous load.
- There are no observed hourly loads, so no observed coincidence, ELCC or reliability claim can be made.
- No Saudi plant output is available to validate the generation model.
- The region mapping, project mounting, commissioning dates and licences are unverified.
- The analysis is descriptive throughout. No causal inference about why projects are where they are.
- Generalisability: the resolution-aware framing transfers to other systems with poor data; the numbers do not.

---

## 8. Journal strategy (no acceptance is implied)

| Journal | Fit | Bar to clear | Likely reviewer concerns | What makes it competitive |
|---|---|---|---|---|
| IET Renewable Power Generation | RE integration and planning inputs | Sound PV/wind modelling, clear EE contribution | "Why not ELCC?"; no validation data | Explicit identification argument (RQ4); thorough uncertainty; open code |
| Energy Reports | Applied energy-system analysis, regional focus | Reproducibility, clear data provenance | Temporal mismatch; descriptive nature | Scenario ranges; database reconciliation; data availability statement |
| Energy Strategy Reviews | Planning and policy relevance | Policy-relevant framing | Engineering depth | Link to firm-capacity assumptions in planning models (L28) |

*Electric Power Systems Research* is a poor fit unless an adequacy model can be built, which needs data that is not public.

---

## 9. Execution roadmap

| Step | Task | Deliverable | Depends on | Decision gate / completion |
|---|---|---|---|---|
| 1 | Download and audit D2, D7, GEM | `audit.json` per dataset | network access | **GO/NO-GO:** D2 regional with ≥ 4 areas; ≥ 80% of capacity locatable |
| 2 | Confirm licences; find official region mapping | licence notes; updated `region_mapping.yaml` | 1 | Redistribution allowed or derived-only release |
| 3 | Read L08, L09, L12, L28 full texts | updated literature matrix | library access | Gap statement confirmed or revised |
| 4 | RQ1 descriptives + supporting analysis B | Fig. 1, tables | 1 | H1 evaluated |
| 5 | Project geocoding, de-duplication, status classes | cleaned project table | 1–2 | Reconciliation report (C) |
| 6 | Weather download; PV/wind model runs | per-project hourly output (≥ 5 years) | 5 | Benchmark CF check |
| 7 | RQ2/RQ3 metrics across all scenarios | Figs. 2–5 | 4–6 | H2, H3 evaluated |
| 8 | RQ4 synthesis; validation (Phase 7) | claim-by-resolution matrix | 7 | Every claim traced to data + transformation |
| 9 | Manuscript | draft | 8 | Only after steps 1–8 are complete |

Steps 1–3 reduce the most uncertainty and need nothing beyond network and library access.
