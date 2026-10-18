"""Build the two project fleets used in RQ2/RQ3 and the source-comparison table (G7).

    python -m scripts.build_projects

Outputs (data/processed/):
  projects_gem.csv        GEM wiki phases, status class, admin region by point-in-polygon
  projects_kapsarc.csv    KAPSARC tracker collapsed to distinct projects (aliases in
                          data/manual/kapsarc_project_aliases.csv); every reported province kept
and results/tables/project_sources_comparison.csv.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from src.projects import status_class

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

ISO_TO_REGION = {
    "SA-01": "Riyadh", "SA-02": "Makkah", "SA-03": "Madinah", "SA-04": "Eastern Province",
    "SA-05": "Al-Qassim", "SA-06": "Hail", "SA-07": "Tabuk", "SA-08": "Northern Borders",
    "SA-09": "Jazan", "SA-10": "Najran", "SA-11": "Al-Baha", "SA-12": "Al-Jouf", "SA-14": "Asir",
}
KAPSARC_PROVINCE = {
    "Al-Jawf Province": "Al-Jouf", "Al-Qassim Province": "Al-Qassim", "Eastern Province": "Eastern Province",
    "Hail Province": "Hail", "Madinah Province": "Madinah", "Makkah Province": "Makkah",
    "Northern Borders Province": "Northern Borders", "Riyadh Province": "Riyadh", "Tabuk Province": "Tabuk",
}
NEAREST_MAX_KM = 15.0  # coastal/offshore points snapped to the nearest province, flagged


def gem_status(raw: str) -> str:
    return "cancelled" if "cancel" in str(raw).lower() else status_class(raw)


def assign_regions(df: pd.DataFrame, gj: dict) -> pd.DataFrame:
    polys = [(ISO_TO_REGION[f["properties"]["iso_3166_2"]], shape(f["geometry"])) for f in gj["features"]]
    regions, flags = [], []
    for lat, lon in zip(df["lat"], df["lon"]):
        pt = Point(lon, lat)
        hit = next((name for name, poly in polys if poly.covers(pt)), None)
        if hit:
            regions.append(hit)
            flags.append("inside")
            continue
        name, dist_deg = min(((n, poly.distance(pt)) for n, poly in polys), key=lambda x: x[1])
        km = dist_deg * 111.0
        regions.append(name if km <= NEAREST_MAX_KM else np.nan)
        flags.append(f"nearest_{km:.1f}km" if km <= NEAREST_MAX_KM else f"unassigned_{km:.0f}km")
    return df.assign(admin_region=regions, region_assignment=flags)


def build_gem(gj: dict) -> pd.DataFrame:
    g = pd.read_csv(P / "gem_phases.csv")
    g["status_class"] = g["status"].map(gem_status)
    g["technology_class"] = np.where(g["tech_category"] == "wind", "wind", "solar")
    g = assign_regions(g, gj)
    g["provenance"] = "gem_only"
    return g


def build_kapsarc() -> pd.DataFrame:
    raw = pd.read_csv(sorted((ROOT / "data/raw/kapsarc/saudi-arabia-planned-and-installed-renewables-by-project").glob("*/export.csv"))[-1])
    aliases = pd.read_csv(ROOT / "data/manual/kapsarc_project_aliases.csv").set_index("raw_project_name")["canonical_project"]
    raw["canonical"] = raw["project_name"].map(aliases).fillna("EXCLUDE_AGGREGATE")
    unmapped = raw.loc[raw["project_name"].notna() & ~raw["project_name"].isin(aliases.index), "project_name"]
    if len(unmapped):
        raise ValueError(f"project names missing from alias table: {sorted(unmapped.unique())}")
    excluded = raw[raw["canonical"] == "EXCLUDE_AGGREGATE"]
    rows = []
    for name, grp in raw[raw["canonical"] != "EXCLUDE_AGGREGATE"].groupby("canonical"):
        provs = sorted({KAPSARC_PROVINCE[p] for p in grp["location"].dropna()})
        rows.append({
            "project": name, "n_records": len(grp), "n_sources": grp["source"].nunique(),
            "technology": "/".join(sorted(grp["type_solar_wind"].unique())),
            "capacity_mw": grp["capacity"].max(), "capacity_mw_min": grp["capacity"].min(),
            "status_raw": "Installed" if (grp["installed_planned"] == "Installed").any() else "Planned",
            "year_first": int(grp["year"].min()), "year_last": int(grp["year"].max()),
            "provinces_reported": ";".join(provs), "province_conflict": len(provs) > 1,
        })
    k = pd.DataFrame(rows)
    k["status_class"] = k["status_raw"].map({"Installed": "installed", "Planned": "planned"})
    k.attrs["excluded_aggregate_rows"] = len(excluded)
    k.attrs["excluded_aggregate_mw"] = float(excluded["capacity"].sum())
    return k


def main() -> None:
    gj = json.loads((P / "sau_admin1_naturalearth.geojson").read_text())
    gem = build_gem(gj)
    gem.to_csv(P / "projects_gem.csv", index=False)
    kap = build_kapsarc()
    kap.to_csv(P / "projects_kapsarc.csv", index=False)

    live = gem[gem["status_class"] != "cancelled"]
    comp = pd.DataFrame([
        {"source": "KAPSARC tracker export (modified 2024-04-03)", "records": 68,
         "distinct_projects": len(kap), "installed_mw": kap.loc[kap.status_class == "installed", "capacity_mw"].sum(),
         "non_installed_mw": kap.loc[kap.status_class != "installed", "capacity_mw"].sum(),
         "located_share_of_mw": kap.loc[kap.provinces_reported != "", "capacity_mw"].sum() / kap["capacity_mw"].sum(),
         "projects_with_province_conflict": int(kap["province_conflict"].sum()),
         "naive_sum_all_records_mw": float(pd.read_csv(sorted((ROOT / "data/raw/kapsarc/saudi-arabia-planned-and-installed-renewables-by-project").glob("*/export.csv"))[-1])["capacity"].sum())},
        {"source": "GEM wiki (retrieved 2026-10-18), excl. cancelled", "records": len(gem),
         "distinct_projects": live["page"].nunique(),
         "installed_mw": live.loc[live.status_class == "installed", "capacity_mw"].sum(),
         "non_installed_mw": live.loc[live.status_class != "installed", "capacity_mw"].sum(),
         "located_share_of_mw": live.loc[live.admin_region.notna(), "capacity_mw"].sum() / live["capacity_mw"].sum(),
         "projects_with_province_conflict": 0, "naive_sum_all_records_mw": gem["capacity_mw"].sum()},
    ])
    comp.round(3).to_csv(ROOT / "results/tables/project_sources_comparison.csv", index=False)
    print(comp.round(2).T.to_string())
    print("\nKAPSARC excluded aggregate rows:", kap.attrs)
    print("\nGEM region assignment:", gem["region_assignment"].str.split("_").str[0].value_counts().to_dict())
    print(kap[kap.province_conflict][["project", "capacity_mw", "provinces_reported"]].to_string(index=False))
    print(live.groupby(["status_class"])["capacity_mw"].sum().round(0).to_dict())


if __name__ == "__main__":
    main()
