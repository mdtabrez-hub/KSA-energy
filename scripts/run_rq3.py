"""RQ3: modelled peak-window capacity factors of the GEM fleet, by operating area.

    python -m scripts.run_rq3            # fetches NASA POWER (cached in data/raw/nasa_power/)

Every number produced here is MODELLED: NASA POWER satellite/reanalysis weather (not ground
measurement) through pvlib/PVWatts or a generic wind power curve. Peak MONTHS are observed
(D2, 2016-2019, duplicates removed); peak HOURS are scenario windows. Nothing here is an ELCC.

Variants: weather years 2019-2023 x {single-axis tracker, fixed tilt} for PV, plus a loss /
temperature-coefficient sensitivity on the tracker case. Wind uses WS50M with two shear
exponents. Solar-thermal (ISCC) fields are excluded from modelling and reported.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import loaders, metrics, wind_model
from src.data_ingestion import ingest_nasa_power_hourly
from src.pipeline import WINDOWS, peak_months
from src.region_mapping import scenarios
from src.renewable_model import PVSystem, per_kw_ac_output

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
T = ROOT / "results" / "tables"
YEARS = [2019, 2020, 2021, 2022, 2023]
AREAS = ["Central", "Eastern", "Southern", "Western"]
PV_VARIANTS = {
    "tracker": PVSystem(tracking=True),
    "fixed": PVSystem(tracking=False),
}
PV_SENS = {
    "tracker_loss10_g030": PVSystem(tracking=True, system_loss=0.10, gamma_pdc=-0.0030),
    "tracker_loss20_g045": PVSystem(tracking=True, system_loss=0.20, gamma_pdc=-0.0045),
}
WIND_VARIANTS = {"wind_a0.10": wind_model.GenericTurbine(shear_alpha=0.10),
                 "wind_a0.20": wind_model.GenericTurbine(shear_alpha=0.20)}


def weather_for(lat: float, lon: float) -> pd.DataFrame:
    key = f"hourly_{lat:.4f}_{lon:.4f}_20190101_20231231"
    cached = sorted(glob.glob(str(ROOT / "data/raw/nasa_power" / key / "*" / "power.json")))
    if not cached:
        folder = ingest_nasa_power_hourly(lat, lon, "20190101", "20231231")
        cached = [str(folder / "power.json")]
        if not Path(cached[0]).exists():
            raise RuntimeError(f"NASA POWER download failed for {lat},{lon}: see {folder}/manifest.json")
    return loaders.nasa_power_weather(cached[-1])


def main() -> None:
    gem = pd.read_csv(P / "projects_gem.csv")
    fleet = gem[(gem["status_class"] != "cancelled") & gem["admin_region"].notna()].copy()
    thermal = fleet["technology"].eq("Solar Thermal")
    excluded = fleet[thermal]
    fleet = fleet[~thermal].reset_index(drop=True)
    fleet.index = fleet.index.astype(str)

    load = pd.read_csv(P / "monthly_load.csv", parse_dates=["date"])
    dups = pd.read_csv(T / "d2_duplicate_years.csv")
    later = {(r.region, r.year_b) for r in dups.itertuples()}
    load = load[[(r, d.year) not in later for r, d in zip(load["region"], load["date"])]]
    area_months = peak_months(load, [2016, 2017, 2018, 2019])

    cache: dict[tuple, pd.DataFrame] = {}
    outputs: dict[str, dict[str, pd.Series]] = {}
    missing_hours = {}
    for pid, row in fleet.iterrows():
        key = (round(row["lat"], 4), round(row["lon"], 4))
        if key not in cache:
            cache[key] = weather_for(*key)
            missing_hours[key] = cache[key].attrs.get("n_missing", 0)
        w = cache[key]
        if row["technology_class"] == "wind":
            for name, turb in WIND_VARIANTS.items():
                outputs.setdefault(name, {})[pid] = wind_model.per_kw_output(
                    w["wind_speed_50m"].fillna(0), ref_height_m=50.0, turbine=turb)
        else:
            wx = w[["ghi", "dni", "dhi", "temp_air"]].fillna(0)
            for name, system in {**PV_VARIANTS, **PV_SENS}.items():
                outputs.setdefault(name, {})[pid] = per_kw_ac_output(row["lat"], row["lon"], wx, system)

    # per-project annual capacity factors (plausibility check of the model, not validation)
    cf_rows = []
    for variant, series in outputs.items():
        for pid, s in series.items():
            for y in YEARS:
                cf_rows.append({"variant": variant, "page": fleet.loc[pid, "page"], "year": y,
                                "annual_cf": float(s[s.index.year == y].mean())})
    cf = pd.DataFrame(cf_rows)
    cf.to_csv(T / "rq3_annual_cf_by_project.csv", index=False)

    # Per-project window CFs, computed once per (variant, year, window, peak-month set);
    # mapping scenarios only regroup projects, so they reuse these values.
    month_sets = {tuple(m) for m in area_months.values()}
    windows = {**WINDOWS, "all_hours": (0, 24)}
    proj_rows = []
    for variant, series in outputs.items():
        for pid, s in series.items():
            idx = s.index
            for y in YEARS:
                in_year = idx.year == y
                for ms in month_sets:
                    for w_name, (h0, h1) in windows.items():
                        mask = in_year & metrics.window_mask(idx, h0, h1, list(ms))
                        proj_rows.append((variant, pid, y, ms, w_name, float(s.to_numpy()[mask].mean())))
    pcf = pd.DataFrame(proj_rows, columns=["variant", "pid", "weather_year", "months", "window", "cf"])
    pcf["capacity_mw"] = pcf["pid"].map(fleet["capacity_mw"])
    pcf["status_class"] = pcf["pid"].map(fleet["status_class"])
    pcf["admin_region"] = pcf["pid"].map(fleet["admin_region"])

    rows = []
    status_sets = {"installed": ["installed"],
                   "all_pipeline": ["installed", "under_construction", "awarded", "planned"]}
    for m_id, mapping in enumerate(scenarios()):
        d = pcf.assign(area=pcf["admin_region"].map(mapping))
        d = d[d["months"] == d["area"].map(lambda a: tuple(area_months[a]))]
        for s_name, statuses in status_sets.items():
            sel = d[d["status_class"].isin(statuses)]
            g = (sel.assign(w=sel["cf"] * sel["capacity_mw"])
                 .groupby(["variant", "weather_year", "area", "window"])
                 .agg(wsum=("w", "sum"), capacity_mw=("capacity_mw", "sum"), n_projects=("pid", "nunique")))
            g["cf"] = g["wsum"] / g["capacity_mw"]
            g = g.drop(columns="wsum").reset_index()
            g["mapping_id"], g["status_set"] = m_id, s_name
            g["tech"] = np.where(g["variant"].str.startswith("wind"), "wind", "pv")
            rows.append(g)
    res = pd.concat(rows, ignore_index=True)
    res.to_csv(T / "rq3_window_cf_scenarios.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

    main_pv = res[res["variant"].isin(PV_VARIANTS)]
    summ = (main_pv.groupby(["status_set", "area", "window"])["cf"]
            .agg(min="min", median="median", max="max", n="size").round(2).reset_index())
    summ.to_csv(T / "rq3_window_cf_summary_pv.csv", index=False)
    by_mount = (main_pv.groupby(["status_set", "variant", "area", "window"])["cf"]
                .agg(min="min", median="median", max="max").round(2).reset_index())
    by_mount.to_csv(T / "rq3_window_cf_by_mounting.csv", index=False)
    sens = (res[res["variant"].str.startswith("tracker")].groupby(["variant", "status_set", "window"])["cf"]
            .median().round(3).unstack("window"))
    sens.to_csv(T / "rq3_loss_sensitivity.csv")
    wind = (res[res["tech"] == "wind"].groupby(["status_set", "variant", "area", "window"])["cf"]
            .agg(min="min", median="median", max="max").round(2).reset_index())
    wind.to_csv(T / "rq3_window_cf_wind.csv", index=False)

    meta = {"peak_months": area_months, "weather_cells": len(cache),
            "weather_missing_hours_total": int(sum(missing_hours.values())),
            "excluded_solar_thermal": excluded[["page", "capacity_mw"]].to_dict("records"),
            "n_projects_modelled": len(fleet)}
    (T / "rq3_metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    pd.set_option("display.width", 250)
    print(json.dumps({k: v for k, v in meta.items() if k != "excluded_solar_thermal"}, default=str))
    print(summ.pivot_table(index=["status_set", "area"], columns="window", values="median").to_string())
    print(by_mount[by_mount.status_set == "installed"].pivot_table(index=["variant", "area"], columns="window", values="median").to_string())
    print(sens.to_string())
    print(wind.pivot_table(index=["status_set", "variant", "area"], columns="window", values="median").to_string())
    print(cf.groupby("variant")["annual_cf"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
