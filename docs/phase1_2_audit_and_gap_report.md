# Phase 1–2 Report: Data Feasibility Audit and Research-Gap Verification

**Project:** Renewable deployment versus regional electricity demand and peak load in Saudi Arabia
**Date of work:** 2026-10-16
**Status:** First deliverable. Phases 3–8 have not started, and no results exist yet.

---

## 0. What was and was not done (read first)

| Task | Done? | Evidence |
|---|---|---|
| Download and inspect KAPSARC files | **No.** No file was downloaded. | Every KAPSARC host (`datasource.kapsarc.org`, `data.kapsarc.org`, `www.kapsarc.org`) was refused by this environment's egress proxy (HTTP 403 on CONNECT). The web-fetch tool also failed (DNS `ENOTFOUND`). Open Net Zero, Crossref, OpenAlex, Semantic Scholar, NASA POWER, Ember and GEM were unreachable in the same way. |
| Verify dataset existence, titles, descriptions and some field lists | **Partly** | Via public search-index snippets of the portal pages (search log W01–W08). This proves a page exists. It does **not** prove row counts, field names, units or completeness. |
| Literature search | **Yes, structured but not systematic** | 17 SciSpace semantic searches plus 8 web searches, logged in `literature/search_log.csv`. Screening used titles and abstracts only. **No full text was read.** This is a *focused literature review*, not a PRISMA systematic review. |
| Reference verification | **Partial** | Titles, authors, year, venue and DOI are taken from SciSpace index metadata. Methods and findings are stated only as far as the abstract supports them. Each row in `literature/literature_matrix.csv` records its access level. |
| Retrieval pipeline | **Yes** | `src/data_ingestion.py` (KAPSARC Explore API v2.1 metadata, CSV export and catalog keyword searches; NASA POWER) and `src/data_validation.py` (schema and quality audit). A live run in this environment recorded the proxy refusal in its manifest, as designed. Unit tests pass (5/5, on hand-made fixtures). |

**To finish Stage A**, run `python -m src.data_ingestion` and then `python -m src.data_validation data/raw/kapsarc/*/*/` from a machine that can reach `datasource.kapsarc.org`. Alternatively, add the KAPSARC hosts to this cloud environment's allowed domains. Every "unverified" cell in the inventory then becomes checkable.

---

## 1. Dataset inventory (most relevant)

The full 20-field inventory is in `data/inventory/dataset_inventory.csv`. Summary:

| # | Dataset (portal title) | ID | Coverage reported | Resolution | Role | Verification |
|---|---|---|---|---|---|---|
| D1 | Electricity Consumption, Subscribers, Peak Load and Actual Generating Capacity **by Region** | `saudi-arabia-electricity-stat-1992-2009` (user-supplied; slug not confirmed) | 1992–2009 | annual (assumed) | Historical regional baseline | Description found in index; slug and schema unverified |
| D2 | **Saudi Arabia Electricity Load Monthly by Region** | `saudi-arabia-electricity-load-monthly-by-region` | 2009–2019 | **monthly max / avg / min load, GW** | **Key series** for seasonal peak structure | Index-verified; file not inspected. Portal notes it is discontinued (an ECRA extract; ECRA is now WERA). |
| D3 | Electricity Installed Capacity (Peak Load) by Region | `installed-generation-capacity-peak-load-in-mw-by-region-for-2014` | 2014 | single year | Regional capacity vs peak cross-check | Index-verified |
| D4 | Total Energy consumption and number of consumers by Category\Region | `energy-consumption-in-mwh-by-region-sector-and-number-of-consumers-for-2007-2014` | 2007–2014 | annual | Regional demand composition | Index-verified |
| D5 | Electricity Consumption by Sectors | `electricity-consumption-by-sectors` | not confirmed | not confirmed | Sector × region (schema snippet shows year, region, sector, MWh) | Schema snippet only |
| D6 | Electricity Consumption, Production, Subscribers, Peak Load and Actual Generating Capacity | `electricity-consumption-production-number-of-subscribers-and-peak-load-1980-2004` | **1980–2019** per snippet (slug says 2004) | annual | National reference | Index-verified; slug and coverage conflict to resolve |
| D7 | **Saudi Arabia Planned and Installed Renewables by Project** | `saudi-arabia-planned-and-installed-renewables-by-project` | tracker reported as of Aug 2026 | project-level, updated quarterly | **Deployment geography and status** | Index-verified. Reported fields: year, source, project, type, capacity (MW), installed/planned status, location, city. Excludes plants < 20 MW and hybrids. |
| X1 | GASTAT Electrical Energy Statistics | publication series | 2010–2023 | annual, 13 administrative regions | Post-2019 regional energy | Methodology page index-verified |
| X2 | GEM Global Solar/Wind Power Trackers | — | current | unit-level coordinates with exact/approximate flag | Independent cross-check of D7 | Wiki pages index-verified; licence unverified |
| X3 | Ember yearly electricity data | — | annual | national | National emissions intensity (illustrative only) | Index-verified |
| X4 | NASA POWER hourly | — | — | hourly, coarse grid | Weather inputs for modelled PV/wind | Unverified (host unreachable) |

**Actual variables and coverage verified for each accessible dataset:** none at file level, because no file was accessible. The variable lists above come from index snippets and are labelled as such.

---

## 2. Feasibility questions A–J

| Q | Question | Status | Evidence |
|---|---|---|---|
| A | Regional demand and peak load after 2009? | **Partially available** | Monthly regional max load 2009–2019 (D2). Regional annual *energy* 2010–2023 by administrative region (X1). No public regional peak series after 2019 was found. Mikayilov et al. used regional annual consumption to 2019 (L01–L02). An Energies 2026 paper (L30, unverified) claims monthly regional data to 2024; its source must be traced. |
| B | Recent regional generating capacity? | **Partially available** | One 2014 cross-section (D3). The 1992–2009 series (D1). No regional capacity series after 2014 was found. |
| C | Renewable project coordinates, capacity, technology, status downloadable? | **Partially available** | D7 has location, capacity, type and status. Whether "location" means coordinates or a nearest city is unverified. X2 gives coordinates with an accuracy flag. |
| D | Actual commissioning dates? | **Requires a proxy** | D7 has a *year* field. Exact commissioning dates were not found and would need SPPC/MoE announcements. |
| E | Map historical electricity regions to project locations reliably? | **Requires a proxy** | No public boundary file for SEC operating areas was found. Administrative regions (13) map approximately, not officially, to the 4 operating areas. This needs documented assumptions and a sensitivity analysis. |
| F | Public hourly or sub-hourly Saudi demand? | **Not found after documented searching** (S13, W04) | Only non-public utility data in the literature (L06, L12, L13) and a synthetic 2015 profile (L27). |
| G | Actual solar/wind generation time series for Saudi plants? | **Not found** | One conference paper uses one PV farm's data (not public). Modelled output cannot be validated against Saudi plant data. |
| H | Emissions factors or generation-mix data? | **Partially available** | National only (Ember X3; L13 annual). No regional or marginal emissions factors. |
| I | Legal reuse and redistribution? | **Unverified** | The KAPSARC and GEM licences could not be read. Keep raw data out of git (`.gitignore`) until they are confirmed. |
| J | Compatible temporal and spatial resolution? | **Partially** | There is a **critical temporal mismatch**: regional peak data end in 2019, while utility-scale RE in KSA is almost entirely 2021 onward. Spatial mismatch also exists (operating areas vs administrative regions vs project points). |

---

## 3. Literature-search log (summary)

The full log is `literature/search_log.csv`. It contains 25 searches: 17 scholarly searches (SciSpace, about 9–10 results each, about 160 hits screened before deduplication) and 8 data-discovery web searches. Screening criteria: Saudi focus or a directly transferable method; a stated method; relevance to regional demand, peak, adequacy, siting, climate coincidence, storage or emissions. Excluded: generic GEP/ELCC papers on other systems (kept only as method references), low-rigour policy pieces with no reproducible method, and duplicates.

**Gaps in the search itself:** Scopus, Web of Science, IEEE Xplore and Google Scholar were not accessible. Full texts were not read. Results are therefore biased towards what SciSpace indexes, and the review must be repeated in a bibliographic database before any manuscript makes a novelty claim.

---

## 4. Literature matrix: closest studies

The full 24-column matrix (30 entries, access level recorded per row) is `literature/literature_matrix.csv`. These are the studies that matter most for the gap decision:

| ID | Study | What it does | Why it matters here |
|---|---|---|---|
| L12 | Yasin et al., IEEE SASG 2022, doi:10.1109/sasg57022.2022.10201226 | Hourly (8760) DC load flow of the **national transmission system**, with N-1 security, RE and storage allocation, and curtailment, under load-growth and deployment scenarios | **Strongest redundancy evidence.** Utility-grade, nodal, hourly assessment of RE location against load exists, using non-public data. A public-data study cannot match its resolution. |
| L06 | Gusmao & Groissböck, IEEE SASG 2015, doi:10.1109/SASG.2015.7449275 | Formal ELCC for one isolated mini-grid in SEC's Southern Operating Area: PV 51.8%, wind 19.4% | Shows PV capacity value can be high in KSA. It is the only Saudi ELCC found. It is not the interconnected grid. |
| L28 | Elshurafa, Petitet & Felder, IEEE SASG 2022, doi:10.1109/sasg57022.2022.10199184 | Saudi capacity expansion model sensitivity to RE firm capacity and forced outage rate | RE firm capacity in Saudi planning models is an **assumption**. Pessimistic values raise battery deployment by up to 41%. This is a genuine open input question. |
| L09 | Alraddadi, Conejo & Lima, JMPCE 2021, doi:10.35833/MPCE.2019.000112 | Stochastic generation, transmission and storage expansion for Saudi Arabia | At high solar shares, night demand drives capacity and storage needs. This is a normative optimisation, not an ex-post assessment. |
| L08 | Elshurafa, Felder & Alhaidari, KAPSARC DP 2022, doi:10.30573/ks--2021-dp23 | Reliability of a high-RE Saudi system under high temperatures | The abstract is truncated, so methods are unknown. **Full text must be read before RQ3 is finalised.** |
| L01–L05 | Mikayilov, Darandary et al. (2020–2025) | Regional annual demand elasticities, projections and cooling sensitivity to 2060 | The regional *energy* demand side is well covered. Regional *peak* and supply geography are not. |
| L13 | Howarth et al., Climate 2020, doi:10.3390/cli8010004 | Hourly temperature–generation link (2011–2015), national | The hourly relationship has been shown nationally with non-public data. |
| L18 | Awan et al., Sustainability 2018, doi:10.3390/su10041129 | PV yield at 44 sites, weighted against national high-load season | The closest precedent for load-season-weighted PV yield. It uses national load only. |
| L29 | Elshurafa & Muhsen, Sustainability 2019, doi:10.3390/su11164301 | Riyadh rooftop PV ceiling of 4.34 GW, about 22% of Central-region peak | A precedent for comparing capacity with a *regional* peak. It is a ratio only, without timing. |
| L10, L11 | Imam et al. 2024; Elkadeem et al. 2025 | GIS-MCDA siting | Siting literature optimises resource and land. Demand location is absent. |

---

## 5. Research-gap evidence matrix

The full table is `literature/gap_matrix.csv`. Verdicts:

| Gap | Verdict | Contribution type | Confidence |
|---|---|---|---|
| G1 Regional demand growth vs peak development | Real but modest; a foundation, not a headline | Empirical-descriptive | Medium |
| G2 Geographic alignment of RE with demand | Plausible gap **in the public literature only**. Utility-internal work (L12) almost certainly covers it, so it must not be claimed as "first". | Empirical | Medium |
| G3 Installed capacity vs peak contribution | Formal ELCC is **infeasible** with public data. A *bounded, scenario-labelled* peak-season contribution is feasible and fills an input gap that L28 shows matters. | Methodological + empirical | Medium-high on infeasibility; medium on novelty |
| G4 Climate-sensitive demand and RE coincidence | Promising when combined with G2 and G3. Observed hourly coincidence is impossible; monthly regional co-movement is testable. | Empirical | Medium |
| G5 Storage and flexibility | Secondary. Use only as a labelled sensitivity. | Scenario | Medium |
| G6 Data-resolution limits | **Strong framing contribution:** formally mapping which claims annual, monthly and hourly public data can identify | Methodological | Medium |
| G7 Project-database uncertainty | Real and measurable. Press reports of the same tracker already disagree on solar share (76% vs 81% of 63.8 GW). | Data / reproducibility | Medium |

---

## 6. Preliminary assessment of the original direction

> *"Beyond Installed Capacity: Assessing the Alignment of Renewable Energy Deployment with Regional Electricity Demand and Peak-Load Requirements in Saudi Arabia"*

| Original RQ | Assessment |
|---|---|
| RQ1 Regional evolution of demand, peak and capacity | **Answerable in part.** Demand and peak to 2019 (monthly peak 2009–2019). Capacity only to 2009 plus 2014. Energy to 2023 by administrative region. |
| RQ2 Geographic alignment of RE with regional demand growth and peak | **Answerable, with caveats.** RE geography is current (2026). Regional peak data stop in 2019. Alignment must be stated against a *2019 structural baseline plus 2023 energy shares*, with explicit region-mapping uncertainty. |
| RQ3 Does generation timing change estimated peak contribution? | **Not answerable as phrased.** No observed hourly load means no observed coincidence and no ELCC. It is answerable only in a **narrowed form**: modelled output at actual project sites during each region's peak *months* (observed), and during explicitly assumed peak *hours* (scenario), with bounds. |
| RQ4 Storage and demand flexibility | **Scenario-only.** Keep as a sensitivity, not a research question. |

**Novelty.** The title implies a novelty ("beyond installed capacity") that is **not established**. Utility planners already assess RE against load at hourly, nodal resolution (L12), and capacity value has been estimated (L06). What the reviewed *public* literature lacks is a **reproducible, public-data, resolution-aware** assessment of the *actual* project fleet against *observed* regional peak structure. That is a narrower but defensible contribution.

**Decision:** **narrow** the original direction. Do not replace it.

---

## 7. Feasibility decision: **CONDITIONAL GO**

**Conditions:**
1. **Narrow RQ3** to a resolution-aware question. Drop formal ELCC, reserve-margin and measured-coincidence claims.
2. **Fix a demand baseline.** Use 2019 monthly regional peaks plus 2023 regional energy shares. State that the analysis compares the *current and planned fleet* with the *most recent observed regional load structure*, not with contemporaneous load.
3. **Region mapping** (administrative region → operating area) must be documented, with at least two alternative mappings tested.
4. **Project status** must be separated (installed / under construction / awarded / tendered / planned) at one snapshot date, with KAPSARC × GEM reconciliation.
5. **All generation is modelled** (pvlib/NASA POWER or ERA5) and labelled as such. Without Saudi plant data, validation is limited to benchmark capacity factors and sensitivity analysis.
6. **Emissions** are out of scope beyond an illustrative national-average bound.

**This becomes NO-GO if** D2 turns out to be national rather than regional on inspection, or D7 lacks usable locations and GEM coordinates cannot substitute. Either finding removes the regional dimension.

### Preliminary candidate directions (formal scoring in Phase 3)

| Candidate | Core question | Feasibility | Novelty (public lit.) | EE relevance | Note |
|---|---|---|---|---|---|
| **A (preferred, provisional)** | *Resolution-aware assessment of the Saudi RE fleet's regional peak-season contribution:* where projects are, how their modelled output aligns with each region's observed monthly peak structure, and what remains unidentifiable without hourly data | Medium (depends on D2 and D7 contents) | Medium | High | Combines G2, G3-bounded, G4, G6 and G7 |
| B | Climate sensitivity of *regional monthly peak load* (2009–2019) vs temperature, by operating area | High | Medium-low (energy-side work exists: L05) | Medium | Could become Section 1 of A |
| C | Reconciliation and uncertainty of Saudi RE project databases | High | Low-medium | Low-medium | A data paper; robustness layer of A |

---

## 8. Evidence needed to finalise the direction (priority order)

1. **Download and audit D2 (monthly load by region).** Confirm the number and names of regions, whether "maximum load" is the instantaneous monthly peak, missing months, and units. *This single file decides GO vs NO-GO.*
2. **Download and audit D7 (renewables by project).** Check whether `location` holds coordinates, the status categories, whether `year` is a commissioning year, record count and duplicates.
3. **Read L08 and L12 in full**, plus the full text of L09 and L28. These determine how much of A is already done internally or by KAPSARC.
4. **Trace L30's data source.** A monthly regional series to 2024 would remove the 2019 cut-off, which is the largest weakness.
5. **Find a defensible operating-area ↔ administrative-region mapping** (SEC or WERA documents, or GASTAT notes).
6. **Confirm licences** for KAPSARC D2/D7 and GEM before redistributing any derived files.
7. **Check whether WERA or the MoE open-data portal publishes regional peak load after 2019.** The MoE lists a "Peak Load" dataset of unknown granularity.
8. **Repeat the literature search** in Scopus or Web of Science (keywords: Saudi AND (peak load OR capacity credit OR ELCC) AND (region* OR spatial)) before any novelty statement.

---

## 9. Follow-up on the evidence list (same day, second pass)

The KAPSARC hosts, Zenodo, NASA POWER, GASTAT and MDPI were still unreachable from this environment, so the evidence list was worked through by search only (log entries S18, W09–W12).

| Item | Result | Effect on the decision |
|---|---|---|
| 1. Is D2 really regional? | **Largely resolved by indirect evidence.** A January 2026 Zenodo archive (L31, Belete, doi:10.5281/zenodo.18252969) forecasts *regional* monthly load from "the KAPSARC Energy Data Portal", 2009–2019. The file itself is still not inspected. | The main NO-GO trigger is now unlikely. It also means regional monthly load **descriptives and forecasting are not new**, so G1 is downgraded to a foundation only. |
| 4. Trace L30's data | **L30 confirmed:** *Energies* 19(17):4038, published 28 Aug 2026. It models monthly regional consumption **per subscriber**, 2009–2024. The data provider is not named in the excerpts. | Monthly regional *energy* data reach 2024, but no regional *peak* series past 2019 has been found. The 2019 peak cut-off remains the main weakness. |
| 7. Regional peak load after 2019 (WERA / MoE) | **Not found.** Two more KAPSARC datasets were found: national peak 1990–2020 (2016–2020 values from WERA) and consumption per customer by region. Secondary sources give national peaks of 62.3 GW (2020) and 63.7 GW (2021). | No change. Next step: WERA's statistics pages (wera.gov.sa), which were not reachable here. |
| 5. Operating-area ↔ province mapping | **Not found.** Sources confirm SEC's four regional business units but list no provinces. | Still requires documented assumptions plus sensitivity. Next source: SEC annual reports. |
| 2, 3, 6, 8 | Not possible from this environment (file downloads, full texts, licence pages, bibliographic databases). | Unchanged |

The decision stays **CONDITIONAL GO**, with somewhat lower data risk on D2. The preferred direction A should not lead with regional load descriptives; its distinct part is the supply-side alignment and peak-season contribution of the actual fleet (G2, G3-bounded, G6, G7).

---

## Sources consulted (data discovery)

- [KAPSARC – Saudi Arabia Electricity Load Monthly by Region](https://datasource.kapsarc.org/explore/assets/saudi-arabia-electricity-load-monthly-by-region/)
- [KAPSARC – Electricity Installed Capacity (Peak Load) by Region, 2014](https://datasource.kapsarc.org/explore/assets/installed-generation-capacity-peak-load-in-mw-by-region-for-2014/?flg=en-gb)
- [KAPSARC – Saudi Arabia Planned and Installed Renewables by Project](https://datasource.kapsarc.org/explore/dataset/saudi-arabia-planned-and-installed-renewables-by-project)
- [KAPSARC – Electricity Consumption by Sectors](https://datasource.kapsarc.org/explore/dataset/electricity-consumption-by-sectors/)
- [KAPSARC – Total Energy consumption and consumers by Category\Region 2007–2014](https://data.kapsarc.org/explore/dataset/energy-consumption-in-mwh-by-region-sector-and-number-of-consumers-for-2007-2014)
- [KAPSARC – Electricity Consumption, Production, Subscribers, Peak Load and Actual Generating Capacity](https://datasource.kapsarc.org/explore/assets/electricity-consumption-production-number-of-subscribers-and-peak-load-1980-2004/)
- [KAPSARC – Saudi Arabia Renewables Tracker](https://devtws.kapsarc.org/our-offerings/simulators/saudi-arabia-renewables-tracker/)
- [TaiyangNews – Saudi solar & wind pipeline exceeds 44 GW](https://taiyangnews.info/markets/saudi-arabia-solar-wind-energy-pipeline-exceeds-44-gw)
- [GASTAT – Methodology and Quality Report for Electrical Energy Statistics](https://www.stats.gov.sa/en/w/methodology-and-quality-report-for-electrical-energy-statistics)
- [GASTAT – Electrical Energy Statistics 2020 (PDF)](https://stats.gov.sa/sites/default/files/Electrical%20Energy%20Statistics%202020EN_0.pdf)
- [GEM wiki – Sudair Solar PV Project](https://www.gem.wiki/Sudair_Solar_PV_Project)
- [Ember – Yearly electricity data](https://ember-energy.org/data/yearly-electricity-data/)
- [Ember – Saudi Arabia](https://ember-energy.org/countries-and-regions/saudi-arabia)
- [Ministry of Energy – Open Data](https://www.moenergy.gov.sa/en/digital-documents/open-data/energy-data)
- [MDPI Energies 19(17):4038 (L30, unverified)](https://www.mdpi.com/1996-1073/19/17/4038)
- [KAPSARC – Electricity Peak Load (national, 1990–2020)](https://datasource.kapsarc.org/explore/dataset/electricity-peak-load/?flg=en-gb)
- [KAPSARC – Electricity Consumption per Customer by Region and Year](https://datasource.kapsarc.org/explore/assets/electricity-consumption-indicators-by-region/)
- [Frontiers in Energy Research 2022 (cites WERA 2010–2020 data)](https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2022.1005081/full)
- [Saudi Electricity Company – Wikipedia (regional business units)](https://en.wikipedia.org/wiki/Saudi_Electricity_Company)
- [MEES – Saudi electricity consumption 2024](https://mees.com/2024/8/16/power-water/saudi-arabias-electricity-consumption-soars-oil-burn-doesnt/c4e9a910-5bcb-11ef-b2c8-9f979049ba5f)
