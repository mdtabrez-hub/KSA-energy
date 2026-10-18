"""Storage sensitivity (illustrative) and Phase-7 validation cross-checks.

    python -m scripts.run_storage_validation

Storage: per operating area (base mapping), the capacity-weighted mean per-kW tracker PV output
of the installed + pipeline fleet in peak months of each weather year is passed through
src.storage with batteries of 0.25-1.0 kW and 1-4 h per kW of PV. Result: mean fraction of
PV nameplate deliverable during 19-22 h. An illustrative sizing bound, not a dispatch study.

Validation:
  V1  D2 annual max of monthly maxima vs D3 regional peak (two KAPSARC tables, both ECRA-derived)
  V2  sum of regional peaks (D3) vs national peak (national KAPSARC series, GASTAT)
  V3  modelled annual PV capacity factors vs the plausibility band 0.18-0.33
"""

from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.run_rq3 import YEARS, weather_for
from src import loaders, metrics, storage
from src.pipeline import peak_months
from src.region_mapping import load_mapping
from src.renewable_model import PVSystem, per_kw_ac_output

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
T = ROOT / "results" / "tables"


def storage_sensitivity() -> pd.DataFrame:
    gem = pd.read_csv(P / "projects_gem.csv")
    fleet = gem[(gem.status_class != "cancelled") & gem.admin_region.notna()
                & (gem.technology_class == "solar") & (gem.technology != "Solar Thermal")]
    mapping = load_mapping()["base"]
    fleet = fleet.assign(area=fleet["admin_region"].map(mapping))
    load = pd.read_csv(P / "monthly_load.csv", parse_dates=["date"])
    months = peak_months(load, [2016, 2017, 2019])
    rows = []
    for area, grp in fleet.groupby("area"):
        series = []
        for _, r in grp.iterrows():
            w = weather_for(round(r.lat, 4), round(r.lon, 4))[["ghi", "dni", "dhi", "temp_air"]].fillna(0)
            series.append(per_kw_ac_output(r.lat, r.lon, w, PVSystem(tracking=True)) * r.capacity_mw)
        agg = sum(series) / grp["capacity_mw"].sum()
        for y in YEARS:
            s = agg[(agg.index.year == y) & np.isin(agg.index.month, months[area])]
            win = metrics.window_mask(s.index, 19, 22)
            for p_kw in (0.25, 0.5, 1.0):
                for hours in (1, 2, 4):
                    b = storage.Battery(power_kw=p_kw, energy_kwh=p_kw * hours)
                    rows.append({"area": area, "weather_year": y, "battery_kw_per_kw_pv": p_kw,
                                 "duration_h": hours, "pv_gw": grp["capacity_mw"].sum() / 1000,
                                 "firm_fraction_19_22": storage.window_firm_fraction(s, win, b)})
    out = pd.DataFrame(rows)
    summ = (out.groupby(["area", "battery_kw_per_kw_pv", "duration_h"])["firm_fraction_19_22"]
            .agg(["min", "median", "max"]).round(3))
    summ.to_csv(T / "storage_sensitivity_19_22.csv")
    return summ


def validation() -> pd.DataFrame:
    load = pd.read_csv(P / "monthly_load.csv", parse_dates=["date"])
    cap = pd.read_csv(P / "regional_capacity_peak_annual.csv")
    d2 = load.assign(year=load.date.dt.year).groupby(["year", "region"])["max"].max().rename("d2_gw")
    v1 = cap.set_index(["year", "region"])["peak_gw"].rename("d3_gw").to_frame().join(d2, how="inner")
    v1["rel_diff"] = (v1["d2_gw"] - v1["d3_gw"]) / v1["d3_gw"]
    nat = pd.read_csv(sorted(glob.glob(str(ROOT / "data/raw/kapsarc/electricity-consumption-production-number-of-subscribers-and-peak-load-1980-2004/*/export.csv")))[-1])
    nat = nat[nat.electricity_indicator == "Peak Load MW"].set_index("time_period")["indicator_value"] / 1000
    v2 = cap.groupby("year")["peak_gw"].sum().rename("sum_regional_gw").to_frame().join(nat.rename("national_gw"))
    v2["diversity_factor"] = v2["sum_regional_gw"] / v2["national_gw"]
    cf = pd.read_csv(T / "rq3_annual_cf_by_project.csv")
    pv = cf[cf.variant.isin(["tracker", "fixed"])]
    v3 = pv.groupby("variant")["annual_cf"].agg(["min", "median", "max",
                                                lambda s: float(((s < 0.18) | (s > 0.33)).mean())])
    v3.columns = ["min", "median", "max", "share_outside_0.18_0.33"]
    v1.round(3).to_csv(T / "validation_v1_d2_vs_d3.csv")
    v2.round(3).to_csv(T / "validation_v2_regional_vs_national_peak.csv")
    v3.round(3).to_csv(T / "validation_v3_pv_cf_plausibility.csv")
    summary = pd.DataFrame({
        "check": ["V1 D2 vs D3 peak, |rel diff| median", "V1 share of region-years within 5%",
                  "V2 diversity factor (sum regional / national) median", "V3 PV project-years outside 0.18-0.33"],
        "value": [v1["rel_diff"].abs().median(), (v1["rel_diff"].abs() <= 0.05).mean(),
                  v2["diversity_factor"].median(), v3["share_outside_0.18_0.33"].max()],
    }).round(3)
    summary.to_csv(T / "validation_summary.csv", index=False)
    print(v2.round(3).to_string())
    return summary


if __name__ == "__main__":
    print(storage_sensitivity().to_string())
    print(validation().to_string(index=False))
