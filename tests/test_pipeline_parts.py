"""Tests for loaders, project reconciliation, wind, storage and the scenario runner.

Every table here is a synthetic fixture built in the test. None of it is KAPSARC, GEM or
NASA POWER data, and no number here is a research result.
"""

import numpy as np
import pandas as pd
import pytest

from src import loaders, pipeline, projects, storage, wind_model
from src.metrics import window_mask
from src.region_mapping import scenarios


# ------------------------------------------------------------------ loaders

def _long_d2():
    rows = []
    for region in ("Central", "Western"):
        for month in pd.date_range("2018-01-01", periods=24, freq="MS"):
            base = 10 + 8 * (month.month in (6, 7, 8, 9))
            for label, f in (("Maximum", 1.0), ("Average", 0.7), ("Minimum", 0.4)):
                rows.append({"Date": month.strftime("%Y-%m"), "Region": region, "Type": label,
                             "Value": base * f + (1 if region == "Western" else 0)})
    return pd.DataFrame(rows)


def test_tidy_monthly_load_long_layout():
    out = loaders.tidy_monthly_load(_long_d2())
    assert list(out.columns) == ["date", "region", "max", "avg", "min", "order_violation"]
    assert len(out) == 48
    assert (out["min"] <= out["avg"]).all() and (out["avg"] <= out["max"]).all()


def test_tidy_monthly_load_wide_layout_and_errors():
    wide = pd.DataFrame({"month": ["2019-07", "2019-08"], "area": ["Eastern"] * 2,
                         "Maximum": [20.0, 21.0], "Average": [15.0, 16.0], "Minimum": [9.0, 9.5]})
    assert loaders.tidy_monthly_load(wide)["max"].tolist() == [20.0, 21.0]
    with pytest.raises(loaders.ColumnMappingError):
        loaders.tidy_monthly_load(pd.DataFrame({"foo": [1], "bar": [2]}))
    bad = _long_d2()
    bad.loc[0, "Type"] = "Median"
    with pytest.raises(ValueError, match="unrecognised"):
        loaders.tidy_monthly_load(bad)


def test_parse_point_formats():
    assert loaders.parse_point("25.77, 45.59") == (25.77, 45.59)
    assert loaders.parse_point({"lat": 28.1, "lon": 35.3}) == (28.1, 35.3)
    assert all(np.isnan(v) for v in loaders.parse_point(None))


def test_nasa_power_parser_converts_time_and_fill_values():
    payload = {"properties": {"parameter": {
        "ALLSKY_SFC_SW_DWN": {"2023070109": 900.0, "2023070110": -999.0},
        "ALLSKY_SFC_SW_DNI": {"2023070109": 700.0, "2023070110": 710.0},
        "ALLSKY_SFC_SW_DIFF": {"2023070109": 150.0, "2023070110": 140.0},
        "T2M": {"2023070109": 41.0, "2023070110": 42.0}}}}
    w = loaders.nasa_power_weather(payload)
    assert w.index[0].hour == 12  # 09 UTC -> 12 local (UTC+3)
    assert np.isnan(w["ghi"].iloc[1]) and w.attrs["n_missing"] == 1


# ------------------------------------------------------------------ projects

def test_status_classes():
    assert projects.status_class("Operating") == "installed"
    assert projects.status_class("Under Construction") == "under_construction"
    assert projects.status_class("pre-construction") == "awarded"
    assert projects.status_class("Tendered (Round 5)") == "tendered"
    assert projects.status_class("???") == "unknown"


def _sources():
    k = pd.DataFrame({"source": "kapsarc", "name": ["Sudair Solar PV", "Al Shuaibah Solar", "Yanbu Wind"],
                      "technology": ["Solar", "Solar", "Wind"], "capacity_mw": [1500.0, 2631.0, 700.0],
                      "status_raw": ["Installed", "Under construction", "Planned"], "year": [2023, 2025, 2026],
                      "lat": [np.nan, 25.6, np.nan], "lon": [np.nan, 42.4, np.nan],
                      "coord_accuracy": ["none", "kapsarc point (accuracy unknown)", "none"], "city": None})
    g = pd.DataFrame({"source": "gem", "name": ["Sudair Solar PV Project", "Shuaibah PV", "Other Solar"],
                      "technology": ["solar"] * 3, "capacity_mw": [1500.0, 2600.0, 300.0],
                      "status_raw": ["operating", "construction", "announced"], "year": np.nan,
                      "lat": [25.7688, 25.62, 20.0], "lon": [45.5872, 42.35, 41.0],
                      "coord_accuracy": ["gem exact", "gem approximate", "gem approximate"], "city": None})
    return k, g


def test_match_and_reconcile_keep_provenance():
    k, g = _sources()
    m = projects.match_sources(k, g)
    assert set(zip(m["kapsarc_idx"], m["gem_idx"])) == {(0, 0), (1, 1)}
    r = projects.reconcile(k, g, m)
    assert len(r) == 4  # two matched, one KAPSARC-only, one GEM-only
    sudair = r[r["name"] == "Sudair Solar PV"].iloc[0]
    assert sudair["lat"] == 25.7688 and sudair["coord_accuracy"] == "gem exact"
    shuaibah = r[r["name"] == "Al Shuaibah Solar"].iloc[0]
    assert shuaibah["lat"] == 25.6  # KAPSARC point preferred over GEM approximate
    assert sorted(r["provenance"]) == ["gem_only", "kapsarc+gem", "kapsarc+gem", "kapsarc_only"]


def test_capacity_tolerance_blocks_match():
    k, g = _sources()
    g.loc[1, "capacity_mw"] = 1000.0
    assert 1 not in set(projects.match_sources(k, g)["kapsarc_idx"])


# ------------------------------------------------------------------ wind and storage

def test_wind_curve_regions():
    v = pd.Series([0.0, 2.0, 8.0, 15.0, 30.0])
    p = wind_model.per_kw_output(v, ref_height_m=120, turbine=wind_model.GenericTurbine(losses=0.0))
    assert p.iloc[0] == 0 and p.iloc[1] == 0 and 0 < p.iloc[2] < 1 and p.iloc[3] == 1 and p.iloc[4] == 0


def test_storage_respects_energy_balance_and_limits():
    idx = pd.date_range("2023-07-01", periods=72, freq="1h", tz="Asia/Riyadh")
    out = pd.Series(np.where((idx.hour >= 8) & (idx.hour < 17), 0.8, 0.0), index=idx)
    win = window_mask(idx, 19, 22)
    batt = storage.Battery(power_kw=0.5, energy_kwh=1.5)
    d = storage.dispatch_into_window(out, win, batt)
    assert ((d["charge"] > 0) & (d["discharge"] > 0)).sum() == 0
    assert d["soc"].min() >= batt.soc_min * batt.energy_kwh - 1e-9
    assert d["soc"].max() <= batt.energy_kwh + 1e-9
    assert d["charge"].sum() * batt.round_trip_eff >= d["discharge"].sum() - 1e-9
    assert (d["charge"] <= out + 1e-12).all()  # no grid charging
    assert storage.window_firm_fraction(out, win, batt) > 0
    assert storage.window_firm_fraction(out, win, storage.Battery(0.0, 0.0)) == 0.0


# ------------------------------------------------------------------ scenario runner

def test_pipeline_end_to_end_on_synthetic_inputs():
    load = loaders.tidy_monthly_load(_long_d2())
    rq1 = pipeline.rq1_peak_structure(load)
    assert set(rq1["peak_month"]) <= {6, 7, 8, 9}
    months = pipeline.peak_months(load, [2019])
    assert months["Central"] == [6, 7, 8, 9]

    proj = pd.DataFrame({"admin_region": ["Riyadh", "Hail", "Tabuk", np.nan],
                         "capacity_mw": [1000.0, 500.0, 400.0, 50.0],
                         "status_class": ["installed", "installed", "planned", "installed"],
                         "provenance": ["kapsarc+gem", "kapsarc_only", "gem_only", "kapsarc_only"]})
    peak = pd.Series({"Central": 18.0, "Western": 19.0, "Eastern": 15.0, "Southern": 6.0})
    rq2 = pipeline.rq2_alignment(proj, peak)
    assert rq2["dissimilarity_vs_peak"].between(0, 1).all()
    assert rq2.attrs["unlocated_capacity_mw"] == 50.0
    # Hail moves between three areas, so the 'installed' set must show more than one D value.
    assert rq2[rq2["status_set"] == "installed"]["dissimilarity_vs_peak"].nunique() > 1

    idx = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="1h", tz="Asia/Riyadh")
    flat = pd.Series(np.where((idx.hour >= 10) & (idx.hour < 16), 1.0, 0.0), index=idx)
    out = {"0": flat, "1": flat, "2": flat}
    area_months = {a: [7, 8] for a in peak.index}
    rq3 = pipeline.rq3_window_cf(proj, out, area_months)
    assert set(rq3["window"]) == set(pipeline.WINDOWS)
    assert rq3.loc[rq3["window"] == "19-22", "cf_window"].eq(0).all()
    assert rq3["mapping_id"].nunique() == len(scenarios())
    summary = pipeline.summarise_range(rq2, ["status_set"], "dissimilarity_vs_peak")
    assert (summary["min"] <= summary["max"]).all()


def test_cli_refuses_to_run_without_inputs(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "PROCESSED", tmp_path)
    assert pipeline.main() == 2
    assert "nothing was computed" in capsys.readouterr().out


# ------------------------------------------------------------------ D2 parsing and corrections

def test_split_kapsarc_indicator_and_reject_unknown():
    raw = pd.DataFrame({"date": ["2019-07", "2019-07"], "value": [20.2, 17.5],
                        "indicator": ["Central region - Maximum - (GW)", "Eastern region - Average (GW)"]})
    out = loaders.split_kapsarc_load_indicator(raw)
    assert out[["region", "type"]].values.tolist() == [["Central", "Maximum"], ["Eastern", "Average"]]
    with pytest.raises(ValueError):
        loaders.split_kapsarc_load_indicator(raw.assign(indicator="Peak load national"))


def test_cleaning_swaps_systematic_labels_and_flags_isolated():
    from src import cleaning
    dates = pd.date_range("2011-01-01", periods=12, freq="MS")
    swapped = pd.DataFrame({"date": dates, "region": "Central", "max": 4.0, "avg": 6.0, "min": 8.0,
                            "order_violation": True})
    ok = pd.DataFrame({"date": dates, "region": "Eastern", "max": 10.0, "avg": 8.0, "min": 6.0,
                       "order_violation": False})
    ok.loc[3, ["max", "avg", "order_violation"]] = [7.0, 8.0, True]
    out, log = cleaning.apply_corrections(pd.concat([swapped, ok], ignore_index=True))
    central = out[out.region == "Central"]
    assert (central["max"] == 8.0).all() and (central["min"] == 4.0).all()
    assert np.isnan(out[(out.region == "Eastern")].iloc[3]["max"])
    assert sorted(log["rule"].unique()) == ["isolated_inconsistency_max_set_nan", "label_swap_sorted"]
