"""Unit tests for geospatial feature engineering."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pricepoint.features.geospatial import (
    BATCH_SIZE,
    FEATURE_COLUMNS,
    TWO_MILES_M,
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


def _distance_columns():
    return [
        "property_id",
        "dist_nearest_school_m",
        "dist_nearest_elementary_m",
        "dist_nearest_middle_m",
        "dist_nearest_high_m",
        "dist_nearest_park_m",
        "dist_nearest_greenway_m",
        "dist_nearest_hospital_m",
    ]


def _agg_columns():
    return [
        "property_id",
        "avg_school_rating_2mi",
        "count_schools_2mi",
        "crime_count_500m_1yr",
        "crime_count_1km_1yr",
        "crime_count_2km_1yr",
        "count_parks_2km",
        "total_park_acres_2km",
    ]


def _contain_columns():
    return [
        "property_id",
        "census_tract_geoid",
        "census_block_group_geoid",
        "subdivision_name",
    ]


def _llm_columns():
    return [
        "property_id",
        "llm_description_score",
        "llm_photo_score",
    ]


def _mock_db_four_queries(
    dist_rows=None,
    agg_rows=None,
    contain_rows=None,
    llm_rows=None,
    pid=1,
):
    """Return a mock session whose .execute() returns four results in order."""
    if dist_rows is None:
        dist_rows = [(pid, 100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0)]
    if agg_rows is None:
        agg_rows = [(pid, 7.5, 3, 5, 10, 25, 4, 120.5)]
    if contain_rows is None:
        contain_rows = [(pid, "37183052403", "371830524031", "Brier Creek")]
    if llm_rows is None:
        llm_rows = [(pid, 8, 7)]

    db = MagicMock()
    db.execute.side_effect = [
        _make_result(_distance_columns(), dist_rows),
        _make_result(_agg_columns(), agg_rows),
        _make_result(_contain_columns(), contain_rows),
        _make_result(_llm_columns(), llm_rows),
    ]
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildGeospatialFeatures:
    """Tests for build_geospatial_features()."""

    def test_returns_dataframe(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        assert isinstance(result, pd.DataFrame)

    def test_index_is_property_id(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        assert result.index.name == "property_id"
        assert list(result.index) == [1]

    def test_has_all_20_feature_columns(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        assert list(result.columns) == FEATURE_COLUMNS
        assert len(result.columns) == 20

    def test_distance_features_populated(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["dist_nearest_school_m"] == 100.0
        assert row["dist_nearest_elementary_m"] == 200.0
        assert row["dist_nearest_middle_m"] == 300.0
        assert row["dist_nearest_high_m"] == 400.0
        assert row["dist_nearest_park_m"] == 150.0
        assert row["dist_nearest_greenway_m"] == 250.0
        assert row["dist_nearest_hospital_m"] == 3000.0

    def test_school_aggregate_features(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["avg_school_rating_2mi"] == 7.5
        assert row["count_schools_2mi"] == 3

    def test_crime_count_features(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["crime_count_500m_1yr"] == 5
        assert row["crime_count_1km_1yr"] == 10
        assert row["crime_count_2km_1yr"] == 25

    def test_crime_density_derived(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        expected = 10 / (math.pi * 1.0**2)
        assert row["crime_density_1km"] == pytest.approx(expected)

    def test_park_aggregate_features(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["count_parks_2km"] == 4
        assert row["total_park_acres_2km"] == 120.5

    def test_containment_features(self):
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["census_tract_geoid"] == "37183052403"
        assert row["census_block_group_geoid"] == "371830524031"
        assert row["subdivision_name"] == "Brier Creek"

    def test_llm_score_features(self):
        db = _mock_db_four_queries()
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

    def test_none_property_ids_queries_all(self):
        """When property_ids is None, queries should not contain filter clause."""
        db = _mock_db_four_queries()
        result = build_geospatial_features(db, property_ids=None)
        assert len(result) == 1
        # Check that no :property_ids param was passed
        for c in db.execute.call_args_list:
            params = c[0][1] if len(c[0]) > 1 else c[1].get("params", {})
            assert "property_ids" not in params

    def test_multiple_properties(self):
        dist_rows = [
            (1, 100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0),
            (2, 110.0, 210.0, 310.0, 410.0, 160.0, 260.0, 3100.0),
        ]
        agg_rows = [
            (1, 7.5, 3, 5, 10, 25, 4, 120.5),
            (2, 8.0, 5, 2, 8, 20, 6, 200.0),
        ]
        contain_rows = [
            (1, "37183052403", "371830524031", "Brier Creek"),
            (2, "37183052404", "371830524041", None),
        ]
        llm_rows = [
            (1, 8, 7),
            (2, 6, 9),
        ]
        db = _mock_db_four_queries(dist_rows, agg_rows, contain_rows, llm_rows)
        result = build_geospatial_features(db, property_ids=[1, 2])
        assert len(result) == 2
        assert result.loc[2, "dist_nearest_school_m"] == 110.0
        assert result.loc[2, "subdivision_name"] is None

    def test_null_containment_values(self):
        """Properties outside all boundaries get None for containment."""
        db = _mock_db_four_queries(
            contain_rows=[(1, None, None, None)],
        )
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["census_tract_geoid"] is None
        assert row["census_block_group_geoid"] is None
        assert row["subdivision_name"] is None

    def test_null_llm_scores(self):
        """Properties without LLM scores get None."""
        db = _mock_db_four_queries(llm_rows=[(1, None, None)])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["llm_description_score"] is None
        assert row["llm_photo_score"] is None

    def test_batching_splits_large_lists(self):
        """Property lists > BATCH_SIZE are split into multiple batches."""
        ids = list(range(1, BATCH_SIZE + 52))  # 151 IDs -> 2 batches

        # We need 8 execute calls: 4 per batch
        dist_rows_1 = [
            (pid, 100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0) for pid in ids[:BATCH_SIZE]
        ]
        agg_rows_1 = [(pid, 7.5, 3, 5, 10, 25, 4, 120.5) for pid in ids[:BATCH_SIZE]]
        contain_rows_1 = [(pid, "37183052403", "371830524031", "Test") for pid in ids[:BATCH_SIZE]]
        llm_rows_1 = [(pid, 8, 7) for pid in ids[:BATCH_SIZE]]

        dist_rows_2 = [
            (pid, 100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0) for pid in ids[BATCH_SIZE:]
        ]
        agg_rows_2 = [(pid, 7.5, 3, 5, 10, 25, 4, 120.5) for pid in ids[BATCH_SIZE:]]
        contain_rows_2 = [(pid, "37183052403", "371830524031", "Test") for pid in ids[BATCH_SIZE:]]
        llm_rows_2 = [(pid, 8, 7) for pid in ids[BATCH_SIZE:]]

        db = MagicMock()
        db.execute.side_effect = [
            # Batch 1
            _make_result(_distance_columns(), dist_rows_1),
            _make_result(_agg_columns(), agg_rows_1),
            _make_result(_contain_columns(), contain_rows_1),
            _make_result(_llm_columns(), llm_rows_1),
            # Batch 2
            _make_result(_distance_columns(), dist_rows_2),
            _make_result(_agg_columns(), agg_rows_2),
            _make_result(_contain_columns(), contain_rows_2),
            _make_result(_llm_columns(), llm_rows_2),
        ]

        result = build_geospatial_features(db, property_ids=ids)
        assert len(result) == len(ids)
        assert db.execute.call_count == 8  # 4 queries * 2 batches

    def test_zero_crime_density(self):
        """Crime density should be 0 when no crime within 1km."""
        db = _mock_db_four_queries(
            agg_rows=[(1, 7.5, 3, 0, 0, 0, 4, 120.5)],
        )
        result = build_geospatial_features(db, property_ids=[1])
        assert result.loc[1, "crime_density_1km"] == 0.0

    def test_no_results_returns_empty(self):
        """When DB returns no rows, return empty DataFrame."""
        db = MagicMock()
        db.execute.side_effect = [
            _make_result(_distance_columns(), []),
            _make_result(_agg_columns(), []),
            _make_result(_contain_columns(), []),
            _make_result(_llm_columns(), []),
        ]
        result = build_geospatial_features(db, property_ids=[999])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_two_miles_constant(self):
        """TWO_MILES_M should be 3218 meters."""
        assert TWO_MILES_M == 3218.0

    def test_feature_columns_count(self):
        """There should be exactly 20 feature columns."""
        assert len(FEATURE_COLUMNS) == 20
