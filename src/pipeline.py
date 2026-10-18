"""Scenario runner for RQ1-RQ3 (docs/phase3_5_research_design.md, section 4).

Inputs are tidy tables (from src.loaders / src.projects) and per-project hourly per-kW output
(from src.renewable_model / src.wind_model). Every result is returned as a long table over
all scenarios, so ranges can be reported and nothing hinges on one unverified assumption.

    python -m src.pipeline   # reads data/processed/*, writes results/tables/*

The CLI stops with a clear message when processed inputs are missing. It never substitutes
placeholder data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from src import metrics
from src.region_mapping import scenarios

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results" / "tables"

WINDOWS = {"12-15": (12, 15), "14-17": (14, 17), "16-19": (16, 19), "19-22": (19, 22)}
STATUS_SETS = {
    "installed": ["installed"],
    "installed+construction": ["installed", "under_construction"],
    "committed": ["installed", "under_construction", "awarded"],
    "all_pipeline": ["installed", "under_construction", "awarded", "tendered", "planned"],
}


# ---------------------------------------------------------------- geography

def assign_admin_region(projects: pd.DataFrame, geojson: dict, name_field: str) -> pd.Series:
    """Point-in-polygon on WGS84 lon/lat. Points outside every polygon get NaN (reported, not forced)."""
    polys = [(f["properties"][name_field], shape(f["geometry"])) for f in geojson["features"]]

    def locate(row):
        if pd.isna(row["lat"]) or pd.isna(row["lon"]):
            return np.nan
        pt = Point(row["lon"], row["lat"])
        for name, poly in polys:
            if poly.covers(pt):
                return name
        return np.nan

    return projects.apply(locate, axis=1)


# ---------------------------------------------------------------- RQ1

def rq1_peak_structure(load: pd.DataFrame) -> pd.DataFrame:
    """Per region and year: peak month, annual max, summer/winter ratio, load factor, growth of the annual max."""
    parts = []
    for region, grp in load.groupby("region"):
        s_max = grp.set_index("date")["max"]
        s_avg = grp.set_index("date")["avg"] if grp["avg"].notna().any() else None
        tab = metrics.monthly_peak_structure(s_max, s_avg)
        tab["growth_pct"] = metrics.growth_rate_pct(tab["annual_max"])
        tab.insert(0, "region", region)
        parts.append(tab.reset_index())
    return pd.concat(parts, ignore_index=True)


def peak_months(load: pd.DataFrame, years: list[int], within: float = 0.05) -> dict[str, list[int]]:
    """Months whose monthly max is within `within` of that year's annual max, pooled over `years`."""
    out = {}
    for region, grp in load.groupby("region"):
        g = grp[grp["date"].dt.year.isin(years)]
        months = set()
        for _, yr in g.groupby(g["date"].dt.year):
            thresh = (1 - within) * yr["max"].max()
            months |= set(yr.loc[yr["max"] >= thresh, "date"].dt.month)
        out[region] = sorted(months)
    return out


# ---------------------------------------------------------------- RQ2

def rq2_alignment(projects: pd.DataFrame, area_peak: pd.Series) -> pd.DataFrame:
    """Dissimilarity index and capacity shares over mapping x status-set x provenance scenarios.

    `projects` needs admin_region, capacity_mw, status_class, provenance.
    `area_peak` is the reference peak per operating area (e.g. 2019 annual max).
    """
    provenance_sets = {
        "all": None,
        "kapsarc_listed": ["kapsarc_only", "kapsarc+gem"],
        "gem_listed": ["gem_only", "kapsarc+gem"],
    }
    rows = []
    located = projects.dropna(subset=["admin_region"])
    for m_id, mapping in enumerate(scenarios()):
        for s_name, statuses in STATUS_SETS.items():
            for p_name, provs in provenance_sets.items():
                sel = located[located["status_class"].isin(statuses)]
                if provs is not None:
                    sel = sel[sel["provenance"].isin(provs)]
                if sel.empty:
                    continue
                cap = sel.groupby(sel["admin_region"].map(mapping))["capacity_mw"].sum()
                row = {"mapping_id": m_id, "status_set": s_name, "provenance_set": p_name,
                       "capacity_mw_total": float(cap.sum()),
                       "dissimilarity_vs_peak": metrics.dissimilarity_index(cap, area_peak)}
                for area, share in metrics.shares(cap.reindex(area_peak.index, fill_value=0)).items():
                    row[f"cap_share_{area}"] = share
                rows.append(row)
    out = pd.DataFrame(rows)
    out.attrs["unlocated_capacity_mw"] = float(projects.loc[projects["admin_region"].isna(), "capacity_mw"].sum())
    return out


# ---------------------------------------------------------------- RQ3

def rq3_window_cf(projects: pd.DataFrame, output: dict[str, pd.Series],
                  area_months: dict[str, list[int]]) -> pd.DataFrame:
    """Capacity-weighted peak-window capacity factor per operating area, window and mapping scenario.

    `output` maps project id (projects.index as str) -> hourly per-kW series (one modelling
    variant). Run once per variant (weather year, mounting, loss set) and concatenate.
    """
    rows = []
    proj = projects.dropna(subset=["admin_region"]).copy()
    proj.index = proj.index.astype(str)
    for m_id, mapping in enumerate(scenarios()):
        area = proj["admin_region"].map(mapping)
        for a in sorted(area.unique()):
            ids = [i for i in proj.index[area == a] if i in output]
            months = area_months.get(a)
            if not ids or not months:
                continue
            for w, (h0, h1) in WINDOWS.items():
                cf = pd.Series({i: metrics.peak_window_capacity_factor(
                    output[i], metrics.window_mask(output[i].index, h0, h1, months)) for i in ids})
                rows.append({"mapping_id": m_id, "area": a, "window": w, "n_projects": len(ids),
                             "cf_window": metrics.capacity_weighted(cf, proj.loc[ids, "capacity_mw"])})
    return pd.DataFrame(rows)


def summarise_range(df: pd.DataFrame, by: list[str], value: str) -> pd.DataFrame:
    """min / median / max of `value` over all remaining scenario dimensions, rounded to 2 sig. fig."""
    g = df.groupby(by)[value]
    out = pd.DataFrame({"min": g.min(), "median": g.median(), "max": g.max(), "n_scenarios": g.size()})
    for c in ("min", "median", "max"):
        out[c] = out[c].map(lambda v: float(f"{v:.2g}"))
    return out.reset_index()


# ---------------------------------------------------------------- CLI

REQUIRED = {
    "monthly_load.csv": "tidy D2 (src.loaders.tidy_monthly_load)",
    "projects.csv": "reconciled projects with admin_region (src.projects.reconcile + assign_admin_region)",
}


def main() -> int:
    missing = [f"{n}: {d}" for n, d in REQUIRED.items() if not (PROCESSED / n).exists()]
    if missing:
        print("Missing processed inputs in data/processed/ - nothing was computed:\n  " + "\n  ".join(missing))
        return 2
    load = pd.read_csv(PROCESSED / "monthly_load.csv", parse_dates=["date"])
    projects = pd.read_csv(PROCESSED / "projects.csv")
    RESULTS.mkdir(parents=True, exist_ok=True)

    rq1 = rq1_peak_structure(load)
    rq1.to_csv(RESULTS / "rq1_peak_structure.csv", index=False)

    ref_year = int(load["date"].dt.year.max())
    area_peak = load[load["date"].dt.year == ref_year].groupby("region")["max"].max()
    rq2 = rq2_alignment(projects, area_peak)
    rq2.to_csv(RESULTS / "rq2_alignment_scenarios.csv", index=False)
    summarise_range(rq2, ["status_set"], "dissimilarity_vs_peak").to_csv(
        RESULTS / "rq2_dissimilarity_summary.csv", index=False)
    meta = {"reference_year": ref_year, "unlocated_capacity_mw": rq2.attrs["unlocated_capacity_mw"],
            "n_mapping_scenarios": len(scenarios())}
    (RESULTS / "run_metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"RQ1/RQ2 written to {RESULTS.relative_to(ROOT)}; RQ3 needs per-project weather runs "
          "(see src.renewable_model) - not run by this CLI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
