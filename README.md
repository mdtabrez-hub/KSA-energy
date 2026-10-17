# KSA-energy

A reproducible research project on how Saudi Arabia's renewable-energy deployment aligns with regional electricity demand and peak load. It uses the KAPSARC Energy Data Portal and other public sources.

## Current status: Phases 1–5 designed; analysis pipeline code-complete; data download pending

1. **`docs/phase1_2_audit_and_gap_report.md`**: dataset inventory, feasibility questions, literature log and matrix, gap matrix, CONDITIONAL GO decision.
2. **`docs/phase3_5_research_design.md`**: chosen direction and scoring, final research questions and hypotheses, methodology, figure plan, journal strategy, roadmap.
3. **`docs/runbook.md`**: the exact commands and decision gates from download to RQ1–RQ3 results.

No data files have been downloaded yet. The KAPSARC portal was unreachable from the environment where this work was done, so every dataset entry is marked by how far it was verified. **No empirical results exist yet.** The only computed table is a clear-sky solar-timing illustration that needs no external data.

## Layout

| Path | Contents |
|---|---|
| `docs/phase1_2_audit_and_gap_report.md` | Phase 1–2 deliverable |
| `data/inventory/dataset_inventory.csv` | 20-field dataset inventory |
| `literature/search_log.csv` | Every search: date, tool, exact query, screening, retained IDs |
| `literature/literature_matrix.csv` | Closest studies, with the access level recorded per row (abstract only, etc.) |
| `literature/gap_matrix.csv` | Candidate research gaps and verdicts |
| `config/data_sources.yaml` | Dataset IDs and API endpoints used by the pipeline |
| `src/data_ingestion.py` | Fetches KAPSARC metadata, CSV exports and catalog searches into `data/raw/` (never overwrites; SHA-256 manifest per run) |
| `src/data_validation.py` | Schema and quality audit of each export (rows, fields, missing values, duplicates, date span, row count vs portal metadata) |
| `src/metrics.py` | Indicator definitions (growth, CAGR, dissimilarity index, peak structure, peak-window capacity factor) |
| `src/renewable_model.py` | pvlib per-kW PV output (tracker or fixed; clear-sky or supplied weather) and solar-noon timing |
| `src/region_mapping.py`, `config/region_mapping.yaml` | Administrative region to operating area mapping (unverified assumption) with all 36 alternative scenarios |
| `src/loaders.py`, `config/column_maps.yaml` | Tidy D2 (long or wide layout), KAPSARC/GEM project tables and NASA POWER weather; schema surprises raise errors |
| `src/projects.py` | Status classes, KAPSARC x GEM matching (name, capacity ±5%, < 25 km), reconciliation with provenance and coordinate preference |
| `src/wind_model.py` | Generic normalised wind power curve with hub-height extrapolation (modelled) |
| `src/storage.py` | Illustrative battery shift into an evening window (no grid charging, SoC limits, energy balance) |
| `src/pipeline.py` | RQ1–RQ3 scenario runner (36 mappings x 4 status sets x 3 source sets x 4 windows); refuses to run without real inputs |
| `scripts/solar_timing_demo.py` | Data-free clear-sky timing illustration -> `results/tables/solar_timing_clearsky.csv` (modelled, clear-sky only) |
| `tests/` | Unit and physical-sanity tests (synthetic fixtures only) |

## Reproduce the data audit

```bash
pip install -r requirements.txt
python -m pytest -q
python -m scripts.solar_timing_demo                  # offline; clear-sky illustration only
python -m src.data_ingestion                         # needs access to datasource.kapsarc.org
python -m src.data_validation data/raw/kapsarc/*/*/  # writes audit.json per dataset
```

`data/raw/` is git-ignored until the reuse licences are confirmed.
