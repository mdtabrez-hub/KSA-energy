#!/usr/bin/env bash
# Reproduce every result table and figure from public sources.
#   ./reproduce.sh            full run: re-download KAPSARC, NASA POWER and Natural Earth (GEM from archive)
#   ./reproduce.sh --verify   then compare outputs with results/SHA256SUMS
# Needs network access to datasource.kapsarc.org, power.larc.nasa.gov and naciscdn.org.
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest -q
python -m src.data_ingestion                         # KAPSARC exports + metadata (new timestamped folder)
python -m src.data_validation data/raw/kapsarc/*/*/  # audit.json per download
python -m scripts.build_processed                    # D2 corrections, D3, consumption, provinces
python -m scripts.fetch_gem_wiki --from-archive      # GEM fleet as archived on 2026-10-18
python -m scripts.build_projects
python -m scripts.run_rq1
python -m scripts.run_rq2
python -m scripts.run_rq3                            # downloads NASA POWER 2019-2023 for ~100 points
python -m scripts.run_storage_validation
python -m scripts.make_figures
if [[ "${1:-}" == "--verify" ]]; then
  sha256sum -c results/SHA256SUMS
fi
