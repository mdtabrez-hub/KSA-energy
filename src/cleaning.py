"""Documented corrections to D2 (monthly load by region). Every change is logged.

Rule 1 (label swap): when every month of a region-year violates min <= avg <= max with the
*same* permutation of the three labels, the labels are taken to be systematically swapped and
the values are re-assigned by sorting. Verified case: Central 2011, where the column labelled
'Minimum' is the largest value in all 12 months.

Rule 2 (isolated inconsistency): any other violating month is kept as published but flagged.
Its `max` is set to NaN for the main analysis, because it is not known which value is wrong.
The sensitivity run (`apply_corrections(..., drop_isolated=False)`) keeps the raw values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _permutation(row) -> tuple:
    vals = {"max": row["max"], "avg": row["avg"], "min": row["min"]}
    return tuple(sorted(vals, key=vals.get))


def apply_corrections(load: pd.DataFrame, drop_isolated: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = load.copy()
    log = []
    out["year"] = out["date"].dt.year
    for (region, year), grp in out.groupby(["region", "year"]):
        viol = grp[grp["order_violation"]]
        if viol.empty:
            continue
        perms = {_permutation(r) for _, r in grp.iterrows()}
        if len(viol) == len(grp) and len(perms) == 1:
            for i, r in grp.iterrows():
                lo, mid, hi = sorted([r["max"], r["avg"], r["min"]])
                log.append({"date": r["date"], "region": region, "rule": "label_swap_sorted",
                            "before": f"max={r['max']} avg={r['avg']} min={r['min']}",
                            "after": f"max={hi} avg={mid} min={lo}"})
                out.loc[i, ["max", "avg", "min"]] = [hi, mid, lo]
                out.loc[i, "order_violation"] = False
        else:
            for i, r in viol.iterrows():
                log.append({"date": r["date"], "region": region,
                            "rule": "isolated_inconsistency_max_set_nan" if drop_isolated else "isolated_inconsistency_kept",
                            "before": f"max={r['max']} avg={r['avg']} min={r['min']}",
                            "after": "max=NaN" if drop_isolated else "unchanged"})
                if drop_isolated:
                    out.loc[i, "max"] = np.nan
    return out.drop(columns="year"), pd.DataFrame(log)
