# KSA-energy

A reproducible research project on how Saudi Arabia's renewable-energy deployment aligns with regional electricity demand and peak load. It uses the KAPSARC Energy Data Portal and other public sources.

## Current status: data downloaded and analysed (2026-10-18); RQ1–RQ3 results and validation complete; draft manuscript v0.1 in `manuscript/`

1. **`docs/phase1_2_audit_and_gap_report.md`**: dataset inventory, feasibility questions, literature log and matrix, gap matrix, CONDITIONAL GO decision.
2. **`docs/phase3_5_research_design.md`**: chosen direction and scoring, final research questions and hypotheses, methodology, figure plan, journal strategy, roadmap.
3. **`docs/runbook.md`**: the exact commands and decision gates from download to RQ1–RQ3 results.
4. **`docs/results_phase6_7.md`**: results, hypothesis verdicts, data-quality findings and validation. Figures are in `results/figures/`.
5. **`docs/data_code_availability_statements.md`**: journal-ready data availability, code availability and reproducibility statements.
6. **`data/README.md`**: what data are in the repository, their licences, and what is re-downloaded.

All findings are descriptive. Generation numbers are modelled, not measured, and nothing here is a reliability or ELCC estimate. Redistributable raw data and processed tables are in `data/`; the rest is re-downloaded by the scripts (see `data/README.md`).

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

## Reproduce everything

```bash
pip install -r requirements-lock.txt   # exact versions used (Python 3.13)
./reproduce.sh --verify                # full pipeline, then checks outputs against results/SHA256SUMS
```

`reproduce.sh` re-downloads the KAPSARC data, NASA POWER weather and Natural Earth boundaries, and rebuilds the GEM fleet from the archived pages. A fresh download may differ where the publishers have revised their data; compare the SHA-256 values in `data/raw/*/<stamp>/manifest.json`.

## Licences

- Code: MIT (`LICENSE`).
- Project-made data tables: CC BY 4.0.
- GEM-derived tables: CC BY-NC-SA.
- KAPSARC data: Public Domain, except three series with no stated licence. See `data/README.md`.
- Cite via `CITATION.cff`.
