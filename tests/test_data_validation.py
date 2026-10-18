"""Tests for the audit helpers. The frames below are hand-made test fixtures, not KAPSARC data."""

import json

import pandas as pd

from src.data_validation import audit_folder, check_coordinates, profile_frame


def test_profile_counts_missing_duplicates_and_negatives():
    df = pd.DataFrame({
        "year": [2010, 2011, 2011, 2012],
        "region": ["Central", "Eastern", "Eastern", None],
        "peak_load_mw": [100.0, -5.0, -5.0, None],
    })
    prof = profile_frame(df)
    cols = {c["name"]: c for c in prof["columns"]}
    assert prof["n_rows"] == 4
    assert prof["duplicate_rows"] == 1
    assert cols["peak_load_mw"]["n_missing"] == 1
    assert cols["peak_load_mw"]["n_negative"] == 2
    assert cols["year"]["span"] == {"first": 2010.0, "last": 2012.0, "n_unparseable": 0}
    assert cols["region"]["values"] == ["Central", "Eastern"]


def test_date_span_reports_unparseable_strings():
    df = pd.DataFrame({"date": ["2019-01", "2019-12", "not a date"]})
    span = profile_frame(df)["columns"][0]["span"]
    assert span["n_unparseable"] == 1
    assert span["first"].startswith("2019-01")


def test_coordinates_outside_saudi_bbox_are_flagged():
    lat = pd.Series([25.77, 51.5, None])
    lon = pd.Series([45.59, -0.12, 40.0])
    assert check_coordinates(lat, lon) == {"n_missing": 1, "n_outside_ksa_bbox": 1}


def test_audit_compares_row_count_with_portal_metadata(tmp_path):
    pd.DataFrame({"a": [1, 2, 3]}).to_csv(tmp_path / "export.csv", index=False)
    meta = {"metas": {"default": {"records_count": 4, "license": "X"}},
            "fields": [{"name": "a"}, {"name": "b"}]}
    (tmp_path / "metadata.json").write_text(json.dumps(meta))
    report = audit_folder(tmp_path)
    assert report["metadata_check"]["match"] is False
    assert report["fields_missing_from_export"] == ["b"]
    assert (tmp_path / "audit.json").exists()


def test_audit_reports_missing_export(tmp_path):
    assert "no export.csv" in audit_folder(tmp_path)["status"]
