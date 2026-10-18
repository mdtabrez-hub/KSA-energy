"""Schema and quality audit for files fetched by src.data_ingestion.

    python -m src.data_validation data/raw/kapsarc/<dataset_id>/<stamp>/

Writes audit.json next to the export and prints a summary. The audit reports what the file
contains (rows, columns, types, missing values, duplicates, date span, region labels) and,
when metadata.json is present, whether the row count matches the portal's records_count.
It does not repair anything: cleaning belongs in a separate, documented step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

DATE_HINTS = ("date", "year", "month", "period", "time")
REGION_HINTS = ("region", "area", "province", "city", "location")


def profile_frame(df: pd.DataFrame) -> dict:
    """Describe a table without altering it."""
    out = {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "columns": [],
        "duplicate_rows": int(df.duplicated().sum()),
    }
    for col in df.columns:
        s = df[col]
        info = {
            "name": str(col),
            "dtype": str(s.dtype),
            "n_missing": int(s.isna().sum()),
            "n_unique": int(s.nunique(dropna=True)),
        }
        lowered = str(col).lower()
        if pd.api.types.is_numeric_dtype(s):
            info["min"] = None if s.dropna().empty else float(s.min())
            info["max"] = None if s.dropna().empty else float(s.max())
            info["n_negative"] = int((s < 0).sum())
        if any(h in lowered for h in DATE_HINTS):
            info["span"] = date_span(s)
        if any(h in lowered for h in REGION_HINTS) and info["n_unique"] <= 60:
            info["values"] = sorted(map(str, s.dropna().unique()))
        out["columns"].append(info)
    return out


def date_span(s: pd.Series) -> dict:
    """First/last values of a date-like column; years stay as numbers rather than being parsed."""
    clean = s.dropna()
    if clean.empty:
        return {"first": None, "last": None, "n_unparseable": 0}
    if pd.api.types.is_numeric_dtype(clean):
        return {"first": float(clean.min()), "last": float(clean.max()), "n_unparseable": 0}
    parsed = pd.to_datetime(clean.astype(str), errors="coerce", format="mixed")
    return {
        "first": None if parsed.dropna().empty else parsed.min().isoformat(),
        "last": None if parsed.dropna().empty else parsed.max().isoformat(),
        "n_unparseable": int(parsed.isna().sum()),
    }


def check_coordinates(lat: pd.Series, lon: pd.Series) -> dict:
    """Flag coordinates outside a generous Saudi bounding box (lat 16-33 N, lon 34-56 E)."""
    lat_n = pd.to_numeric(lat, errors="coerce")
    lon_n = pd.to_numeric(lon, errors="coerce")
    missing = lat_n.isna() | lon_n.isna()
    outside = ~missing & ~(lat_n.between(16, 33) & lon_n.between(34, 56))
    return {"n_missing": int(missing.sum()), "n_outside_ksa_bbox": int(outside.sum())}


def compare_with_metadata(n_rows: int, metadata_path: Path) -> dict:
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    default = meta.get("metas", {}).get("default", {})
    reported = default.get("records_count")
    return {
        "records_count_reported": reported,
        "rows_in_export": n_rows,
        "match": reported == n_rows if reported is not None else None,
        "license": default.get("license"),
        "modified": default.get("modified"),
        "publisher": default.get("publisher"),
        "fields_reported": [f.get("name") for f in meta.get("fields", [])],
    }


def audit_folder(folder: Path) -> dict:
    export = folder / "export.csv"
    if not export.exists():
        return {"folder": str(folder), "status": "no export.csv - download failed or not attempted"}
    df = pd.read_csv(export)
    report = {"folder": str(folder), "status": "audited", "profile": profile_frame(df)}
    metadata = folder / "metadata.json"
    if metadata.exists():
        report["metadata_check"] = compare_with_metadata(len(df), metadata)
        reported_fields = set(report["metadata_check"]["fields_reported"])
        report["fields_missing_from_export"] = sorted(reported_fields - set(map(str, df.columns)))
    (folder / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for arg in argv:
        report = audit_folder(Path(arg))
        prof = report.get("profile", {})
        print(f"{arg}: {report['status']}; rows={prof.get('n_rows')} cols={prof.get('n_cols')} "
              f"dupes={prof.get('duplicate_rows')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
