"""Retrieve KAPSARC dataset metadata and exports into an immutable raw-data store.

Usage (from the repo root, on a machine that can reach the KAPSARC portal):

    python -m src.data_ingestion                  # metadata + CSV export for every configured dataset
    python -m src.data_ingestion --catalog-only   # only run the catalog keyword searches
    python -m src.data_ingestion --ids saudi-arabia-electricity-load-monthly-by-region

Every run writes to data/raw/<source>/<dataset_id>/<UTC timestamp>/ and never overwrites
an earlier run. Each folder gets a manifest.json recording the request URL, HTTP status,
download time, byte size and SHA-256 of every file, so the audit can cite exactly what was
received. Failed requests are recorded too: a missing dataset is an audit finding, not an
error to hide.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "data_sources.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
TIMEOUT_S = 60


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def run_folder(source: str, dataset_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = RAW_DIR / source / dataset_id / stamp
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def fetch(url: str, params: dict | None = None) -> dict:
    """GET a URL and return a record of the attempt, including the body when it succeeds."""
    record = {
        "url": url,
        "params": params or {},
        "requested_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT_S)
        record["status_code"] = resp.status_code
        record["final_url"] = resp.url
        record["content_type"] = resp.headers.get("Content-Type")
        record["body"] = resp.content
    except requests.RequestException as exc:
        record["status_code"] = None
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["body"] = None
    return record


def save(folder: Path, filename: str, record: dict) -> dict:
    """Write the body (if any) and return the manifest entry for it."""
    entry = {k: v for k, v in record.items() if k != "body"}
    body = record.get("body")
    if body is not None and record.get("status_code") == 200:
        target = folder / filename
        target.write_bytes(body)
        entry.update(file=filename, bytes=len(body), sha256=sha256_bytes(body))
    return entry


def ingest_kapsarc_dataset(dataset_id: str, api_bases: list[str]) -> Path:
    """Fetch metadata JSON and a full CSV export, trying each portal host in turn."""
    folder = run_folder("kapsarc", dataset_id)
    manifest = {"dataset_id": dataset_id, "attempts": []}
    for base in api_bases:
        meta = fetch(f"{base}/catalog/datasets/{quote(dataset_id)}")
        manifest["attempts"].append(save(folder, "metadata.json", meta))
        if meta.get("status_code") != 200:
            continue
        export = fetch(
            f"{base}/catalog/datasets/{quote(dataset_id)}/exports/csv",
            params={"delimiter": ",", "with_bom": "false"},
        )
        manifest["attempts"].append(save(folder, "export.csv", export))
        manifest["host_used"] = base
        break
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


def search_kapsarc_catalog(term: str, api_bases: list[str], limit: int = 100) -> Path:
    """Record the raw catalog hits for one keyword so the search is auditable."""
    folder = run_folder("kapsarc_catalog", term.replace(" ", "_"))
    manifest = {"term": term, "attempts": []}
    for base in api_bases:
        rec = fetch(
            f"{base}/catalog/datasets",
            params={"where": f'search("{term}")', "limit": limit},
        )
        manifest["attempts"].append(save(folder, "catalog.json", rec))
        if rec.get("status_code") == 200:
            manifest["host_used"] = base
            break
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


def ingest_nasa_power_hourly(lat: float, lon: float, start: str, end: str,
                             parameters: str = "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,T2M,WS10M,WS50M") -> Path:
    """Fetch modelled hourly weather at one point. These are model inputs, never plant output."""
    dataset_id = f"hourly_{lat:.4f}_{lon:.4f}_{start}_{end}"
    folder = run_folder("nasa_power", dataset_id)
    rec = fetch(
        "https://power.larc.nasa.gov/api/temporal/hourly/point",
        params={
            "parameters": parameters,
            "community": "RE",
            "latitude": lat,
            "longitude": lon,
            "start": start,
            "end": end,
            "format": "JSON",
            "time-standard": "UTC",
        },
    )
    manifest = {"dataset_id": dataset_id, "attempts": [save(folder, "power.json", rec)]}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ids", nargs="*", help="Only these KAPSARC dataset IDs")
    parser.add_argument("--catalog-only", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config()
    bases = cfg["kapsarc"]["api_bases"]
    failures = 0

    for term in cfg["kapsarc"]["catalog_search_terms"]:
        folder = search_kapsarc_catalog(term, bases)
        ok = (folder / "catalog.json").exists()
        failures += not ok
        print(f"catalog '{term}': {'ok' if ok else 'FAILED'} -> {folder.relative_to(REPO_ROOT)}")
    if args.catalog_only:
        return 1 if failures else 0

    wanted = set(args.ids or [])
    for ds in cfg["kapsarc"]["datasets"]:
        if wanted and ds["id"] not in wanted:
            continue
        folder = ingest_kapsarc_dataset(ds["id"], bases)
        ok = (folder / "export.csv").exists()
        failures += not ok
        print(f"dataset {ds['id']}: {'ok' if ok else 'FAILED'} -> {folder.relative_to(REPO_ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
