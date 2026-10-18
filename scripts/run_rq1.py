"""RQ1: regional peak, capacity and demand structure from KAPSARC data (downloaded 2026-10-18).

    python -m scripts.run_rq1

Inputs (data/processed/, built from data/raw/ by the steps logged in docs/results_log.md):
  monthly_load.csv                   D2 after src.cleaning corrections
  regional_capacity_peak_annual.csv  D3 (ECRA/WERA regional peak, installed, available capacity)
  regional_consumption_annual.csv    regional total consumption 2005-2025
Duplicated D2 years (results/tables/d2_duplicate_years.csv) are excluded from year-specific
statistics and counted once in pooled seasonal statistics.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src import metrics
from src.pipeline import peak_months

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
T = ROOT / "results" / "tables"


def duplicate_years() -> dict[str, set[int]]:
    """Region -> years whose monthly values are copies of another year (both members flagged)."""
    d = pd.read_csv(T / "d2_duplicate_years.csv")
    out: dict[str, set[int]] = {}
    for _, r in d.iterrows():
        out.setdefault(r["region"], set()).update({int(r["year_a"]), int(r["year_b"])})
    return out


def second_copies() -> dict[str, set[int]]:
    """Region -> the later year of each duplicated pair (dropped so the pattern counts once)."""
    d = pd.read_csv(T / "d2_duplicate_years.csv")
    out: dict[str, set[int]] = {}
    for _, r in d.iterrows():
        out.setdefault(r["region"], set()).add(int(r["year_b"]))
    return out


def main() -> None:
    load = pd.read_csv(P / "monthly_load.csv", parse_dates=["date"])
    cap = pd.read_csv(P / "regional_capacity_peak_annual.csv")
    cons = pd.read_csv(P / "regional_consumption_annual.csv")
    dups, later = duplicate_years(), second_copies()

    # --- seasonal structure from D2 (flag duplicated years)
    rows = []
    for region, grp in load.groupby("region"):
        s = grp.set_index("date")
        tab = metrics.monthly_peak_structure(s["max"], s["avg"])
        tab["duplicate_year_flag"] = tab.index.isin(dups.get(region, set()))
        tab.insert(0, "region", region)
        rows.append(tab.reset_index())
    seasonal = pd.concat(rows, ignore_index=True)
    seasonal.to_csv(T / "rq1_seasonal_structure_d2.csv", index=False)

    # suspected outliers: monthly max more than 1.8x the monthly average (typical ratio ~1.3)
    ratio = load["max"] / load["avg"]
    anomalies = load.assign(max_to_avg=ratio.round(2))[ratio > 1.8]
    anomalies.to_csv(T / "d2_anomalies_max_to_avg.csv", index=False)
    print(f"suspected outliers (retained, flagged): {anomalies[['date', 'region', 'max', 'avg']].to_dict('records')}")

    dedup = load[~load.apply(lambda r: r["date"].year in later.get(r["region"], set()), axis=1)]
    pm = peak_months(dedup, [2016, 2017, 2018, 2019])
    pooled = (seasonal[~seasonal["duplicate_year_flag"]]
              .groupby("region")
              .agg(n_years=("year", "size"),
                   peak_month_mode=("peak_month", lambda x: int(x.mode().iloc[0])),
                   summer_winter_ratio_median=("summer_winter_ratio", "median"),
                   summer_winter_ratio_min=("summer_winter_ratio", "min"),
                   summer_winter_ratio_max=("summer_winter_ratio", "max"),
                   load_factor_median=("load_factor", "median")))
    pooled["peak_months_2016_2019_within5pct"] = pooled.index.map(lambda r: ",".join(map(str, pm[r])))
    pooled.round(3).to_csv(T / "rq1_seasonal_summary.csv")

    # --- annual peak and capacity trends from D3
    trend = []
    for region, g in cap.groupby("region"):
        g = g.set_index("year").sort_index()
        y0, y1 = g.index.min(), g.index.max()
        trend.append({
            "region": region, "first_year": int(y0), "last_year": int(y1),
            "peak_first_gw": g.loc[y0, "peak_gw"], "peak_last_gw": g.loc[y1, "peak_gw"],
            "peak_cagr_pct": metrics.cagr_pct(g.loc[y0, "peak_gw"], g.loc[y1, "peak_gw"], y1 - y0),
            "peak_cagr_2015_2019_pct": metrics.cagr_pct(g.loc[2015, "peak_gw"], g.loc[2019, "peak_gw"], 4),
            "installed_cagr_pct": metrics.cagr_pct(g.loc[y0, "installed_gw"], g.loc[y1, "installed_gw"], y1 - y0),
            "installed_to_peak_2019": g.loc[y1, "installed_gw"] / g.loc[y1, "peak_gw"],
            "available_to_peak_2019": g.loc[y1, "available_gw"] / g.loc[y1, "peak_gw"]
            if not np.isnan(g.loc[y1, "available_gw"]) else np.nan,
            "regional_surplus_installed_minus_peak_2019_gw": g.loc[y1, "installed_gw"] - g.loc[y1, "peak_gw"],
        })
    pd.DataFrame(trend).round(3).to_csv(T / "rq1_peak_capacity_trends_d3.csv", index=False)

    # --- consumption to 2025
    c = cons.pivot(index="year", columns="region", values="electricity_consumption_mwh")
    ctab = pd.DataFrame({
        "cagr_2005_2019_pct": [metrics.cagr_pct(c.loc[2005, r], c.loc[2019, r], 14) for r in c],
        "cagr_2019_2025_pct": [metrics.cagr_pct(c.loc[2019, r], c.loc[2025, r], 6) for r in c],
        "twh_2019": c.loc[2019] / 1e6, "twh_2025": c.loc[2025] / 1e6,
        "share_2019": metrics.shares(c.loc[2019]), "share_2025": metrics.shares(c.loc[2025]),
    }, index=c.columns)
    ctab.round(3).to_csv(T / "rq1_consumption_growth.csv")

    print(pooled.round(2).to_string())
    print(pd.DataFrame(trend).round(2).to_string(index=False))
    print(ctab.round(3).to_string())


if __name__ == "__main__":
    main()
