"""Build data/processed/ from data/raw/ (latest download of each source).

    python -m scripts.build_processed

  monthly_load.csv (+ _sensitivity_raw_isolated)  D2 split, tidied, corrected (src.cleaning)
  regional_capacity_peak_annual.csv              D3 pivoted to peak / installed / available GW
  regional_consumption_annual.csv                regional totals from the sector table
  sau_admin1_naturalearth.geojson                Natural Earth admin-1, Saudi provinces
Also writes results/tables/d2_corrections_log.csv and d2_duplicate_years.csv.
"""

from __future__ import annotations

import glob
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import shapefile

from src import cleaning, loaders

ROOT = Path(__file__).resolve().parents[1]
P, T = ROOT / "data/processed", ROOT / "results/tables"
NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"


def latest(dataset: str) -> pd.DataFrame:
    return pd.read_csv(sorted(glob.glob(str(ROOT / f"data/raw/kapsarc/{dataset}/*/export.csv")))[-1])


def duplicate_years(load: pd.DataFrame) -> pd.DataFrame:
    rows = []
    load = load.assign(y=load.date.dt.year, m=load.date.dt.month)
    for region, g in load.groupby("region"):
        for col in ("max", "avg", "min"):
            p = g.pivot(index="m", columns="y", values=col)
            for a in p.columns:
                for b in p.columns:
                    if b > a and (p[a] == p[b]).sum() >= 10:
                        rows.append((region, col, a, b, int((p[a] == p[b]).sum())))
    return pd.DataFrame(rows, columns=["region", "measure", "year_a", "year_b", "identical_months_of_12"])


def natural_earth() -> None:
    folder = ROOT / "data/raw/naturalearth"
    shp = sorted(folder.glob("*/ne_10m_admin_1_states_provinces.shp"))
    if not shp:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = folder / stamp
        dest.mkdir(parents=True)
        blob = requests.get(NE_URL, timeout=300).content
        (dest / "SHA256SUMS").write_text(f"{hashlib.sha256(blob).hexdigest()}  ne_10m_admin_1_states_provinces.zip\n")
        zipfile.ZipFile(io.BytesIO(blob)).extractall(dest)
        shp = [dest / "ne_10m_admin_1_states_provinces.shp"]
    r = shapefile.Reader(str(shp[-1]), encoding="utf-8")
    fields = [f[0] for f in r.fields[1:]]
    feats = []
    for sr in r.iterShapeRecords():
        rec = dict(zip(fields, sr.record))
        if rec["adm0_a3"] == "SAU":
            feats.append({"type": "Feature", "geometry": sr.shape.__geo_interface__,
                          "properties": {"name": rec["name"], "iso_3166_2": rec["iso_3166_2"]}})
    (P / "sau_admin1_naturalearth.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))


def main() -> None:
    P.mkdir(parents=True, exist_ok=True)
    T.mkdir(parents=True, exist_ok=True)
    raw = loaders.tidy_monthly_load(
        loaders.split_kapsarc_load_indicator(latest("saudi-arabia-electricity-load-monthly-by-region")),
        on_order_violation="flag")
    load, log = cleaning.apply_corrections(raw)
    load.to_csv(P / "monthly_load.csv", index=False)
    cleaning.apply_corrections(raw, drop_isolated=False)[0].to_csv(P / "monthly_load_sensitivity_raw_isolated.csv", index=False)
    log.to_csv(T / "d2_corrections_log.csv", index=False)
    duplicate_years(load).to_csv(T / "d2_duplicate_years.csv", index=False)

    cap = latest("installed-generation-capacity-peak-load-in-mw-by-region-for-2014").pivot_table(
        index=["year", "area"], columns="indicator", values="value_gw").reset_index()
    cap.columns.name = None
    cap.rename(columns={"Peak Load": "peak_gw", "Installed Generation Capacity": "installed_gw",
                        "Available Capacities": "available_gw", "area": "region"}).to_csv(
        P / "regional_capacity_peak_annual.csv", index=False)

    s = latest("electricity-consumption-by-sectors")
    s[(s.sector == "Total") & (s.region != "Total")][["year", "region", "electricity_consumption_mwh"]].to_csv(
        P / "regional_consumption_annual.csv", index=False)
    natural_earth()
    print(f"processed tables written; D2 corrections: {log['rule'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
