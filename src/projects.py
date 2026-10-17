"""Project status classes, KAPSARC x GEM reconciliation, and coordinate choice.

Nothing here merges records silently. Matches need agreement on name, capacity and distance;
everything unmatched is kept and labelled with its source.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

STATUS_CLASSES = ["installed", "under_construction", "awarded", "tendered", "planned", "unknown"]

_STATUS_RULES = [
    ("installed", r"\b(installed|operating|operational|commissioned|in operation)\b"),
    ("under_construction", r"(under construction|construction)"),
    ("awarded", r"(awarded|ppa signed|financial close|pre-construction)"),
    ("tendered", r"(tender|bid|shortlist|rfq|rfp)"),
    ("planned", r"(planned|announced|proposed|development|pipeline|future)"),
]


def status_class(raw: str) -> str:
    """Map a free-text status onto one class. Ambiguous text maps to 'unknown', not a guess."""
    text = str(raw).strip().lower()
    hits = [cls for cls, pat in _STATUS_RULES if re.search(pat, text)]
    # 'pre-construction' would also hit 'construction'; prefer the more specific rule order.
    if "pre-construction" in text:
        return "awarded"
    return hits[0] if hits else "unknown"


def normalise_name(name: str) -> str:
    text = str(name).lower()
    text = re.sub(r"\b(solar|pv|photovoltaic|wind|farm|project|power|plant|ipp|park|phase|the)\b", " ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return " ".join(text.split())


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def match_sources(kapsarc: pd.DataFrame, gem: pd.DataFrame, cap_tol: float = 0.05,
                  max_km: float = 25.0) -> pd.DataFrame:
    """One-to-one matches between tidy KAPSARC and GEM tables.

    A pair matches when normalised names share a token, capacities differ by at most cap_tol
    (relative), and, where both have coordinates, they lie within max_km. The closest capacity
    wins ties. Returns pairs of row indices with the evidence used.
    """
    rows = []
    used_gem: set[int] = set()
    for ki, k in kapsarc.iterrows():
        k_tokens = set(normalise_name(k["name"]).split())
        best = None
        for gi, g in gem.iterrows():
            if gi in used_gem or not k_tokens & set(normalise_name(g["name"]).split()):
                continue
            rel = abs(k["capacity_mw"] - g["capacity_mw"]) / max(k["capacity_mw"], g["capacity_mw"])
            if rel > cap_tol:
                continue
            dist = np.nan
            if pd.notna(k["lat"]) and pd.notna(g["lat"]):
                dist = float(haversine_km(k["lat"], k["lon"], g["lat"], g["lon"]))
                if dist > max_km:
                    continue
            if best is None or rel < best[1]:
                best = (gi, rel, dist)
        if best:
            used_gem.add(best[0])
            rows.append({"kapsarc_idx": ki, "gem_idx": best[0], "cap_rel_diff": best[1], "dist_km": best[2]})
    return pd.DataFrame(rows, columns=["kapsarc_idx", "gem_idx", "cap_rel_diff", "dist_km"])


def reconcile(kapsarc: pd.DataFrame, gem: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Unified project table: matched pairs once, unmatched from either source, with provenance.

    Coordinate preference: GEM 'exact' > KAPSARC point > GEM approximate > none. KAPSARC
    capacity and status are kept for matched pairs (it is the primary source); GEM values are
    retained in *_gem columns so disagreements stay visible.
    """
    out = []
    matched_k = set(matches["kapsarc_idx"])
    matched_g = set(matches["gem_idx"])
    for _, mrow in matches.iterrows():
        k = kapsarc.loc[mrow["kapsarc_idx"]]
        g = gem.loc[mrow["gem_idx"]]
        lat, lon, acc = _pick_coords(k, g)
        out.append({**k.to_dict(), "lat": lat, "lon": lon, "coord_accuracy": acc,
                    "provenance": "kapsarc+gem", "capacity_mw_gem": g["capacity_mw"],
                    "status_raw_gem": g["status_raw"]})
    for ki, k in kapsarc.iterrows():
        if ki not in matched_k:
            out.append({**k.to_dict(), "provenance": "kapsarc_only"})
    for gi, g in gem.iterrows():
        if gi not in matched_g:
            out.append({**g.to_dict(), "provenance": "gem_only"})
    df = pd.DataFrame(out)
    df["status_class"] = df["status_raw"].map(status_class)
    return df


def _pick_coords(k: pd.Series, g: pd.Series):
    if pd.notna(g["lat"]) and "exact" in str(g["coord_accuracy"]):
        return g["lat"], g["lon"], g["coord_accuracy"]
    if pd.notna(k["lat"]):
        return k["lat"], k["lon"], k["coord_accuracy"]
    if pd.notna(g["lat"]):
        return g["lat"], g["lon"], g["coord_accuracy"]
    return np.nan, np.nan, "none"
