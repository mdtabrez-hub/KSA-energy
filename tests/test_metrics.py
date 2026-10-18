"""Tests for indicator definitions. All inputs are hand-made fixtures."""

import numpy as np
import pandas as pd
import pytest

from src import metrics as m


def test_growth_rate_skips_gaps_in_years():
    s = pd.Series([100.0, 110.0, 121.0, 150.0], index=[2010, 2011, 2012, 2014])
    g = m.growth_rate_pct(s)
    assert np.isnan(g[2010]) and np.isnan(g[2014])
    assert g[2011] == pytest.approx(10.0) and g[2012] == pytest.approx(10.0)


def test_cagr_matches_constant_growth():
    assert m.cagr_pct(100, 100 * 1.05 ** 10, 10) == pytest.approx(5.0)
    with pytest.raises(ValueError):
        m.cagr_pct(0, 10, 5)


def test_dissimilarity_bounds_and_missing_regions():
    demand = pd.Series({"Central": 40, "Western": 40, "Eastern": 20})
    assert m.dissimilarity_index(demand * 3, demand) == pytest.approx(0.0)
    # All supply in a region with no demand -> complete mismatch.
    assert m.dissimilarity_index(pd.Series({"Northern": 5.0}), demand) == pytest.approx(1.0)
    supply = pd.Series({"Central": 50, "Western": 50})
    assert m.dissimilarity_index(supply, demand) == pytest.approx(0.2)


def test_shares_reject_negative_and_zero_total():
    with pytest.raises(ValueError):
        m.shares(pd.Series([1, -1]))
    with pytest.raises(ValueError):
        m.shares(pd.Series([0, 0]))


def test_monthly_peak_structure():
    idx = pd.date_range("2018-01-01", periods=12, freq="MS")
    mx = pd.Series([30, 29, 31, 35, 40, 45, 50, 52, 47, 38, 33, 32.0], index=idx)
    avg = mx * 0.7
    out = m.monthly_peak_structure(mx, avg).loc[2018]
    assert out["peak_month"] == 8
    assert out["annual_max"] == 52
    assert out["summer_winter_ratio"] == pytest.approx(52 / 32)
    assert out["load_factor"] == pytest.approx(0.7 * mx.mean() / 52)
    assert out["n_months"] == 12


def test_peak_window_capacity_factor_and_weighting():
    idx = pd.date_range("2023-07-01", periods=48, freq="1h", tz="Asia/Riyadh")
    out = pd.Series(np.where((idx.hour >= 12) & (idx.hour < 15), 0.8, 0.0), index=idx)
    assert m.peak_window_capacity_factor(out, m.window_mask(idx, 12, 15)) == pytest.approx(0.8)
    assert m.peak_window_capacity_factor(out, m.window_mask(idx, 19, 22)) == 0.0
    with pytest.raises(ValueError):
        m.peak_window_capacity_factor(out, m.window_mask(idx, 12, 15, months=[1]))
    cf = pd.Series({"a": 0.6, "b": 0.2})
    assert m.capacity_weighted(cf, pd.Series({"a": 300, "b": 100})) == pytest.approx(0.5)
