"""RQ2: regional distribution of RE capacity vs regional peak load and demand.

    python -m scripts.run_rq2

Reference distributions: 2019 regional peak (D3, last year available) and 2025 regional
consumption (KAPSARC sector table). Scenarios: 36 admin-region -> operating-area mappings x
status sets x (for KAPSARC) every combination of conflicting reported provinces.
All results are descriptive geography; D says nothing about transmission adequacy.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pandas as pd

from src import metrics
from src.pipeline import STATUS_SETS
from src.region_mapping import scenarios

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
T = ROOT / "results" / "tables"
AREAS = ["Central", "Eastern", "Southern", "Western"]


def references() -> dict[str, pd.Series]:
    cap = pd.read_csv(P / "regional_capacity_peak_annual.csv")
    cons = pd.read_csv(P / "regional_consumption_annual.csv")
    return {
        "peak_2019": cap[cap.year == 2019].set_index("region")["peak_gw"].reindex(AREAS),
        "consumption_2025": cons[cons.year == 2025].set_index("region")["electricity_consumption_mwh"].reindex(AREAS),
    }


def evaluate(fleet: pd.DataFrame, region_col: str, refs: dict, labels: dict) -> list[dict]:
    rows = []
    for m_id, mapping in enumerate(scenarios()):
        for s_name, statuses in STATUS_SETS.items():
            sel = fleet[fleet["status_class"].isin(statuses) & fleet[region_col].notna()]
            if sel.empty:
                continue
            cap = sel.groupby(sel[region_col].map(mapping))["capacity_mw"].sum().reindex(AREAS, fill_value=0.0)
            row = {**labels, "mapping_id": m_id, "status_set": s_name, "capacity_gw": cap.sum() / 1000}
            for ref_name, ref in refs.items():
                row[f"D_vs_{ref_name}"] = metrics.dissimilarity_index(cap, ref)
            for a in AREAS:
                row[f"share_{a}"] = cap[a] / cap.sum()
                row[f"gw_{a}"] = cap[a] / 1000
            rows.append(row)
    return rows


def summarise(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    cols = ["capacity_gw", "D_vs_peak_2019", "D_vs_consumption_2025"] + [f"share_{a}" for a in AREAS]
    g = df.groupby(by)[cols]
    out = pd.concat({"min": g.min(), "median": g.median(), "max": g.max()}, axis=1)
    out.columns = [f"{c}_{s}" for s, c in out.columns]
    return out.join(df.groupby(by).size().rename("n_scenarios")).round(3)


def main() -> None:
    refs = references()
    gem = pd.read_csv(P / "projects_gem.csv")
    gem = gem[gem["status_class"] != "cancelled"]
    rows = evaluate(gem, "admin_region", refs, {"source": "GEM"})
    rows += evaluate(gem[gem["capacity_mw"] >= 20], "admin_region", refs, {"source": "GEM >=20MW"})

    kap = pd.read_csv(P / "projects_kapsarc.csv").fillna({"provinces_reported": ""})
    options = [p.split(";") if p else [None] for p in kap["provinces_reported"]]
    for combo_id, combo in enumerate(product(*options)):
        k = kap.assign(admin_region=list(combo))
        rows += evaluate(k, "admin_region", refs, {"source": "KAPSARC", "province_combo": combo_id})

    df = pd.DataFrame(rows)
    df.to_csv(T / "rq2_alignment_scenarios.csv", index=False)
    summary = summarise(df, ["source", "status_set"])
    summary.to_csv(T / "rq2_alignment_summary.csv")
    shares = pd.DataFrame({k: metrics.shares(v) for k, v in refs.items()}).round(3)
    shares.to_csv(T / "rq2_reference_shares.csv")
    pd.set_option("display.width", 250)
    print("Reference shares:\n", shares.to_string())
    keep = ["n_scenarios", "capacity_gw_median", "D_vs_peak_2019_min", "D_vs_peak_2019_median", "D_vs_peak_2019_max",
            "D_vs_consumption_2025_median"] + [f"share_{a}_{s}" for a in AREAS for s in ("min", "max")]
    print(summary[keep].to_string())


if __name__ == "__main__":
    main()
