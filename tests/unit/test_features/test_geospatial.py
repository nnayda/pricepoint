"""Unit tests for geospatial feature engineering."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd

from pricepoint.features.geospatial import (
    FEATURE_COLUMNS,
    build_geospatial_features,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(columns: list[str], rows: list[tuple]):
    """Create a mock DB result with .fetchall() and .keys()."""
    mock = MagicMock()
    mock.fetchall.return_value = rows
    mock.keys.return_value = columns
    return mock


def _geo_lookup_columns():
    return [
        "property_id",
        "avg_school_rating",
        "avg_school_drive",
        "dist_nearest_school_m",
        "dist_nearest_elementary_m",
        "dist_nearest_middle_m",
        "dist_nearest_high_m",
        "dist_nearest_park_m",
        "dist_nearest_greenway_m",
        "dist_nearest_hospital_m",
        "in_noise_zone",
        "in_critical_risk_zone",
        "county_subdivision_geoid",
    ]


def _history_columns():
    return [
        "property_id",
        "avg_days_on_market_1m",
        "avg_days_on_market_3m",
        "avg_days_on_market_1y",
        "median_sale_price_1m",
        "median_sale_price_3m",
        "median_sale_price_1y",
    ]


def _llm_columns():
    return [
        "property_id",
        "llm_description_score",
        "llm_photo_score",
    ]


def _default_geo_row(pid: int):
    return (pid, 7.5, 12.3, 100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0, 0, 1, "37183001")


def _default_history_row(pid: int):
    return (pid, 30.0, 28.5, 25.0, 350000.0, 345000.0, 340000.0)


def _default_llm_row(pid: int):
    return (pid, 8, 7)


def _mock_db(
    pids: list[int],
    geo_rows=None,
    history_rows=None,
    llm_rows=None,
):
    """Return a mock session that returns results for 3 queries: geo, history, llm."""
    if geo_rows is None:
        geo_rows = [_default_geo_row(pid) for pid in pids]
    if history_rows is None:
        history_rows = [_default_history_row(pid) for pid in pids]
    if llm_rows is None:
        llm_rows = [_default_llm_row(pid) for pid in pids]

    db = MagicMock()
    db.execute.side_effect = [
        _make_result(_geo_lookup_columns(), geo_rows),
        _make_result(_history_columns(), history_rows),
        _make_result(_llm_columns(), llm_rows),
    ]
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildGeospatialFeatures:
    """Tests for build_geospatial_features()."""

    def test_returns_dataframe(self):
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert isinstance(result, pd.DataFrame)

    def test_index_is_property_id(self):
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert result.index.name == "property_id"
        assert list(result.index) == [1]

    def test_has_all_19_feature_columns(self):
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert list(result.columns) == FEATURE_COLUMNS
        assert len(result.columns) == 19

    def test_geo_lookup_features_populated(self):
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["avg_school_rating"] == 7.5
        assert row["avg_school_drive"] == 12.3
        assert row["dist_nearest_school_m"] == 100.0
        assert row["dist_nearest_elementary_m"] == 200.0
        assert row["dist_nearest_middle_m"] == 300.0
        assert row["dist_nearest_high_m"] == 400.0
        assert row["dist_nearest_park_m"] == 150.0
        assert row["dist_nearest_greenway_m"] == 250.0
        assert row["dist_nearest_hospital_m"] == 3000.0
        assert row["in_noise_zone"] == 0
        assert row["in_critical_risk_zone"] == 1

    def test_history_metrics_populated(self):
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["avg_days_on_market_1m"] == 30.0
        assert row["avg_days_on_market_3m"] == 28.5
        assert row["avg_days_on_market_1y"] == 25.0
        assert row["median_sale_price_1m"] == 350000.0
        assert row["median_sale_price_3m"] == 345000.0
        assert row["median_sale_price_1y"] == 340000.0

    def test_llm_score_features(self):
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["llm_description_score"] == 8
        assert row["llm_photo_score"] == 7

    def test_empty_property_ids_returns_empty_frame(self):
        db = MagicMock()
        result = build_geospatial_features(db, property_ids=[])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        db.execute.assert_not_called()

    def test_multiple_properties(self):
        geo_rows = [
            (1, 7.5, 12.3, 100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0, 0, 1, "37183001"),
            (2, 8.0, 10.5, 110.0, 210.0, 310.0, 410.0, 160.0, 260.0, 3100.0, 1, 0, "37183002"),
        ]
        history_rows = [
            _default_history_row(1),
            _default_history_row(2),
        ]
        llm_rows = [
            (1, 8, 7),
            (2, 6, 9),
        ]
        db = _mock_db(
            pids=[1, 2],
            geo_rows=geo_rows,
            history_rows=history_rows,
            llm_rows=llm_rows,
        )
        result = build_geospatial_features(db, property_ids=[1, 2])
        assert len(result) == 2
        assert result.loc[2, "dist_nearest_school_m"] == 110.0
        assert result.loc[2, "in_noise_zone"] == 1

    def test_null_llm_scores(self):
        """Properties without LLM scores get None."""
        db = _mock_db(pids=[1], llm_rows=[(1, None, None)])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["llm_description_score"] is None
        assert row["llm_photo_score"] is None

    def test_no_results_returns_empty(self):
        """When DB returns no geo rows, return empty DataFrame."""
        db = MagicMock()
        db.execute.side_effect = [
            _make_result(_geo_lookup_columns(), []),
            _make_result(_history_columns(), []),
            _make_result(_llm_columns(), []),
        ]
        result = build_geospatial_features(db, property_ids=[999])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_feature_columns_count(self):
        """There should be exactly 19 feature columns."""
        assert len(FEATURE_COLUMNS) == 19

    def test_county_subdivision_geoid_not_in_output(self):
        """county_subdivision_geoid is used for joining but not as a feature."""
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert "county_subdivision_geoid" not in result.columns

    def test_missing_history_metrics_are_nan(self):
        """Properties without history metrics get NaN."""
        db = _mock_db(pids=[1], history_rows=[])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert pd.isna(row["avg_days_on_market_1m"])
        assert pd.isna(row["median_sale_price_1y"])

    def test_none_property_ids_queries_all(self):
        """When property_ids is None, queries should not filter."""
        db = _mock_db(pids=[1])
        result = build_geospatial_features(db, property_ids=None)
        assert len(result) == 1
        # 3 queries: geo lookup, history, llm
        assert db.execute.call_count == 3
