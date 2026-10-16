# KSA-energy

A reproducible research project on how Saudi Arabia's renewable-energy deployment aligns with regional electricity demand and peak load. It uses the KAPSARC Energy Data Portal and other public sources.

## Current status: Phases 1–2 complete (2026-10-16), decision CONDITIONAL GO

Start with **`docs/phase1_2_audit_and_gap_report.md`**. It contains the dataset inventory, the feasibility questions, the literature log and matrix, the gap matrix, the assessment of the original research direction, and the list of evidence still needed.

No data files have been downloaded yet. The KAPSARC portal was unreachable from the environment where this work was done, so every dataset entry is marked by how far it was verified. **No results exist yet.**

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
| `tests/` | Unit tests for the audit helpers (synthetic fixtures only) |

## Reproduce the data audit

```bash
pip install -r requirements.txt
python -m pytest -q
python -m src.data_ingestion                         # needs access to datasource.kapsarc.org
python -m src.data_validation data/raw/kapsarc/*/*/  # writes audit.json per dataset
```

`data/raw/` is git-ignored until the reuse licences are confirmed.
