# Runbook: from download to RQ1–RQ3 results

Every step below is code-complete and tested on synthetic fixtures. None has been run on real data yet, because the data hosts are unreachable from the environment the code was written in. Run the steps in order on a machine with network access, and stop at each gate.

| # | Command / action | Output | Gate |
|---|---|---|---|
| 1 | `python -m src.data_ingestion` | `data/raw/kapsarc/<id>/<stamp>/{metadata.json, export.csv, manifest.json}` and catalog searches | Every configured dataset has `export.csv`. Missing ones are findings to record in the inventory. |
| 2 | `python -m src.data_validation data/raw/kapsarc/*/*/` | `audit.json` per dataset | **GO/NO-GO:** D2 has ≥ 4 regions with monthly max/avg/min. Record the real field names in `config/column_maps.yaml` and the inventory. |
| 3 | Read `metadata.json` `license` for D2 and D7; check the GEM terms | licence note in inventory | Decide whether derived tables can be published (`data/processed/` stays git-ignored until then). |
| 4 | `loaders.tidy_monthly_load(pd.read_csv(<D2 export>))` → `data/processed/monthly_load.csv` | tidy D2 | Loader raises on any unexpected schema; fix the column map, never the data. |
| 5 | Download the GEM solar/wind tracker XLSX manually (download form) to `data/raw/gem/` | raw GEM file | — |
| 6 | `loaders.tidy_projects(..., "kapsarc")`, `loaders.tidy_projects(..., "gem")`, `projects.match_sources`, `projects.reconcile` | unified project table with provenance | Inspect unmatched records by hand; document any manual matches in a CSV, never in code. |
| 7 | Get admin-region polygons (geoBoundaries or GADM, ADM1; licence checked) as GeoJSON; `pipeline.assign_admin_region(...)` → `data/processed/projects.csv` | projects with `admin_region` | Report unlocated capacity (MW). If it is > 20% of the total, stop and improve geocoding. |
| 8 | Replace `config/region_mapping.yaml` with an official mapping if one is found; otherwise keep the 36 scenarios | — | — |
| 9 | `python -m src.pipeline` | `results/tables/rq1_peak_structure.csv`, `rq2_alignment_scenarios.csv`, `rq2_dissimilarity_summary.csv`, `run_metadata.json` | H1 and H2 evaluated as specified in the design document §3 |
| 10 | For each located project and ≥ 5 weather years: `data_ingestion.ingest_nasa_power_hourly(lat, lon, start, end)` → `loaders.nasa_power_weather` → `renewable_model.per_kw_ac_output` (tracker *and* fixed) or `wind_model.per_kw_output` | per-project hourly per-kW series | Report missing-hour counts. Compare annual CFs with any sourced official plant figures. |
| 11 | `pipeline.rq3_window_cf(projects, output, pipeline.peak_months(load, [2017, 2018, 2019]))` per modelling variant; concatenate; `pipeline.summarise_range` | RQ3 ranges | H3 evaluated; reported as min–median–max only |
| 12 | `storage.window_firm_fraction` for 1–4 h batteries per area and window | storage sensitivity | Labelled illustrative sizing bound |

The region names in D2 must match the operating-area names in `config/region_mapping.yaml` (Central, Eastern, Western, Southern). If D2 uses other labels, add an explicit rename table. Do not edit the source file.
