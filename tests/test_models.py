"""Physical sanity checks for the PV model and the region-mapping enumeration."""

import pandas as pd
import pytest

from src.region_mapping import aggregate_to_areas, load_mapping, scenarios
from src.renewable_model import PVSystem, clearsky_weather, per_kw_ac_output, solar_noon_local


@pytest.fixture(scope="module")
def july_riyadh():
    idx = pd.date_range("2023-07-21", periods=24, freq="1h", tz="Asia/Riyadh")
    return per_kw_ac_output(24.71, 46.68, clearsky_weather(24.71, 46.68, idx, 40.0))


def test_pv_output_is_bounded_and_zero_at_night(july_riyadh):
    assert july_riyadh.between(0, 1).all()
    assert july_riyadh.iloc[0:4].eq(0).all() and july_riyadh.iloc[21:24].eq(0).all()
    assert july_riyadh.max() > 0.5


def test_heat_reduces_output():
    idx = pd.date_range("2023-07-21 12:00", periods=1, freq="1h", tz="Asia/Riyadh")
    cool = per_kw_ac_output(24.71, 46.68, clearsky_weather(24.71, 46.68, idx, 15.0), PVSystem(dc_ac_ratio=1.0))
    hot = per_kw_ac_output(24.71, 46.68, clearsky_weather(24.71, 46.68, idx, 45.0), PVSystem(dc_ac_ratio=1.0))
    assert hot.iloc[0] < cool.iloc[0]


def test_solar_noon_shifts_with_longitude():
    # 11 degrees of longitude ~ 44 minutes of solar time under one clock (UTC+3).
    west = solar_noon_local(21.54, 39.17, "2023-07-21")
    east = solar_noon_local(26.43, 50.10, "2023-07-21")
    minutes = (west - east).total_seconds() / 60
    assert 40 < minutes < 48


def test_region_mapping_scenarios_cover_alternatives():
    cfg = load_mapping()
    maps = scenarios(cfg)
    assert len(maps) == 3 * 3 * 2 * 2
    assert maps[0] == cfg["base"]
    assert {m["Hail"] for m in maps} == {"Central", "Eastern", "Western"}
    assert all(len(m) == 13 for m in maps)


def test_aggregate_refuses_unmapped_regions():
    mapping = load_mapping()["base"]
    vals = pd.Series({"Riyadh": 10.0, "Al-Qassim": 5.0, "Makkah": 7.0})
    assert aggregate_to_areas(vals, mapping).to_dict() == {"Central": 15.0, "Western": 7.0}
    with pytest.raises(KeyError):
        aggregate_to_areas(pd.Series({"Atlantis": 1.0}), mapping)
