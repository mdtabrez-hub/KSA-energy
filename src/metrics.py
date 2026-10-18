"""Indicator definitions used in the research design (docs/phase3_5_research_design.md, section 5).

Every function here is a plain transformation of its inputs. None of them is a reliability
metric: a capacity-to-peak ratio is not a reserve margin, and a peak-window capacity factor
is not an ELCC. The docstrings say what each quantity can and cannot be read as.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def growth_rate_pct(series: pd.Series) -> pd.Series:
    """g[t] = 100 * (X[t] / X[t-1] - 1). A year whose predecessor is missing stays NaN."""
    s = series.sort_index()
    prev = s.shift(1)
    consecutive = pd.Series(s.index, index=s.index).diff() == 1
    return (100 * (s / prev - 1)).where(consecutive)


def cagr_pct(first: float, last: float, years: float) -> float:
    """Compound annual growth rate between two observations `years` apart."""
    if first <= 0 or last <= 0 or years <= 0:
        raise ValueError("CAGR needs positive values and a positive span")
    return 100 * ((last / first) ** (1 / years) - 1)


def shares(values: pd.Series) -> pd.Series:
    """Normalise non-negative regional values to shares summing to 1."""
    if (values < 0).any():
        raise ValueError("shares need non-negative values")
    total = values.sum()
    if total == 0:
        raise ValueError("cannot take shares of an all-zero series")
    return values / total


def dissimilarity_index(supply: pd.Series, demand: pd.Series) -> float:
    """Duncan dissimilarity D = 0.5 * sum_r |s_r - d_r| between two regional distributions.

    D is the fraction of supply that would have to sit in a different region for its regional
    distribution to match demand's. It lies in [0, 1]. It says nothing about whether the grid
    can move power between regions, so it is a planning-geography indicator, not an adequacy one.
    """
    regions = supply.index.union(demand.index)
    s = shares(supply.reindex(regions, fill_value=0.0))
    d = shares(demand.reindex(regions, fill_value=0.0))
    return float(0.5 * (s - d).abs().sum())


def capacity_to_peak_ratio(capacity_mw: pd.Series, peak_mw: pd.Series) -> pd.Series:
    """Descriptive installed-capacity / observed-peak ratio per region (NOT a reserve margin)."""
    return capacity_mw / peak_mw


def monthly_peak_structure(monthly_max: pd.Series, monthly_avg: pd.Series | None = None) -> pd.DataFrame:
    """Seasonal peak descriptors per year from a monthly series indexed by Timestamp.

    Returns, per calendar year: the month of the annual maximum, the annual maximum, the
    summer/winter ratio (max of Jun-Sep over max of Dec-Feb in the same calendar year), and,
    when monthly averages are given, the annual load factor (mean of monthly averages / annual
    maximum). Years with fewer than 12 months are flagged rather than dropped.
    """
    s = monthly_max.sort_index()
    rows = []
    for year, grp in s.groupby(s.index.year):
        months = grp.index.month
        summer = grp[(months >= 6) & (months <= 9)]
        winter = grp[(months == 12) | (months <= 2)]
        row = {
            "year": year,
            "n_months": int(grp.notna().sum()),
            "peak_month": int(grp.idxmax().month) if grp.notna().any() else np.nan,
            "annual_max": float(grp.max()),
            "summer_winter_ratio": float(summer.max() / winter.max())
            if len(summer) and len(winter) else np.nan,
        }
        if monthly_avg is not None:
            avg = monthly_avg.reindex(grp.index)
            row["load_factor"] = float(avg.mean() / grp.max())
        rows.append(row)
    return pd.DataFrame(rows).set_index("year")


def window_mask(index: pd.DatetimeIndex, start_hour: int, end_hour: int,
                months: list[int] | None = None) -> np.ndarray:
    """Boolean mask for local clock hours start_hour <= h < end_hour, optionally in some months."""
    hours = index.hour
    mask = (hours >= start_hour) & (hours < end_hour)
    if months is not None:
        mask &= np.isin(index.month, months)
    return np.asarray(mask)


def peak_window_capacity_factor(per_kw_output: pd.Series, mask: np.ndarray) -> float:
    """A[r] = mean of per-unit output over the hours in a stated peak window T_peak.

    With modelled output and an *assumed* window this is a scenario quantity: the average
    fraction of nameplate available during those hours. It is not observed coincidence and
    not an ELCC.
    """
    selected = per_kw_output[mask]
    if selected.empty:
        raise ValueError("peak window selects no hours")
    return float(selected.mean())


def capacity_weighted(values: pd.Series, capacity_mw: pd.Series) -> float:
    """Capacity-weighted mean of per-project values (e.g. peak-window capacity factors)."""
    w = capacity_mw.reindex(values.index)
    if w.isna().any() or (w <= 0).any():
        raise ValueError("every project needs a positive capacity")
    return float((values * w).sum() / w.sum())
