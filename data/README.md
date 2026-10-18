# Data in this repository

Everything was downloaded on **2026-10-18**. Each download folder holds the original files unmodified, a `manifest.json` (request URL, HTTP status, retrieval time, byte size, SHA-256) and, for KAPSARC, the portal `metadata.json` and an `audit.json`.

| Folder | Source | Licence | In the repository? |
|---|---|---|---|
| `raw/kapsarc/<dataset>/<stamp>/` | KAPSARC Energy Data Portal (datasource.kapsarc.org), Explore API v2.1 | **Public Domain** (portal metadata) for 7 datasets | Yes: export, metadata, manifest, audit |
| same, for `saudi-arabia-electricity-load-monthly-by-region`, `electricity-peak-load`, `the-growth-of-the-peak-loads-according-to-sources-in-the-electricity-sector-mw` | KAPSARC (original source ECRA/WERA) | **No licence stated** on the portal | Metadata, manifest (with SHA-256) and audit only. `export.csv` is re-downloaded by `python -m src.data_ingestion` |
| `raw/kapsarc_catalog/` | KAPSARC catalog keyword searches | portal terms | Yes |
| `raw/gem_wiki/<stamp>/` | Global Energy Monitor wiki, 106 project pages (Global Solar/Wind Power Tracker) | **CC BY-NC-SA** | Yes: archived HTML + SHA-256 manifest |
| `raw/nasa_power/` | NASA POWER hourly API, 2019–2023, ~100 points (461 MB) | free use with attribution | No: re-downloaded by `scripts/run_rq3.py` |
| `raw/naturalearth/` | Natural Earth 1:10m admin-1 (49 MB) | public domain | No: re-downloaded by `scripts/build_processed.py` |
| `processed/` | built by the scripts | inherits from the sources | Yes, except `monthly_load*.csv` (derived from the unlicensed D2 series) |
| `manual/kapsarc_project_aliases.csv` | hand-made identity table for KAPSARC project records | CC BY 4.0 (this project) | Yes |
| `inventory/dataset_inventory.csv` | dataset inventory | CC BY 4.0 (this project) | Yes |

**Attribution required when reusing:**
- KAPSARC Energy Data Portal.
- "Global Energy Monitor, Global Solar Power Tracker / Global Wind Power Tracker (gem.wiki), CC BY-NC-SA".
- "NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program".
- Natural Earth.

GEM-derived files (`processed/gem_phases.csv`, `processed/projects_gem.csv` and the RQ2/RQ3 result tables) may be reused only non-commercially, and derivatives must be shared alike.

**Upstream changes:** KAPSARC datasets are revised by the portal; for example, D3 and D2 were modified on 2026-05-05. NASA POWER also releases new versions. A fresh download can therefore differ from the 2026-10-18 snapshot. Compare the SHA-256 in each `manifest.json` to see whether it does.
