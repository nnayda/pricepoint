"""Unit tests for geospatial feature engineering."""

from __future__ import annotations

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


def _school_agg_columns():
    return [
        "property_id",
        "avg_school_rating_2mi",
        "count_schools_2mi",
    ]


def _park_agg_columns():
    return [
        "property_id",
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


def _make_dist_results(pids: list[int], values: dict[int, tuple] | None = None):
    """Build the 7 individual distance query results.

    *values* maps property_id -> (school, elementary, middle, high, park, greenway, hospital).
    """
    defaults = {pid: (100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0) for pid in pids}
    if values:
        defaults.update(values)

    dist_names = [
        "dist_nearest_school_m",
        "dist_nearest_elementary_m",
        "dist_nearest_middle_m",
        "dist_nearest_high_m",
        "dist_nearest_park_m",
        "dist_nearest_greenway_m",
        "dist_nearest_hospital_m",
    ]

    results = []
    for i, name in enumerate(dist_names):
        rows = [(pid, defaults[pid][i]) for pid in pids]
        results.append(_make_result(["property_id", name], rows))
    return results


def _mock_db_queries(
    pids: list[int] | None = None,
    dist_values: dict[int, tuple] | None = None,
    school_agg_rows=None,
    park_agg_rows=None,
    contain_rows=None,
    llm_rows=None,
):
    """Return a mock session for the per-feature query structure.

    Per batch: 7 distance + school_agg + park_agg + containment + llm = 11 calls.
    """
    if pids is None:
        pids = [1]

    if school_agg_rows is None:
        school_agg_rows = [(pid, 7.5, 3) for pid in pids]
    if park_agg_rows is None:
        park_agg_rows = [(pid, 4, 120.5) for pid in pids]
    if contain_rows is None:
        contain_rows = [(pid, "37183052403", "371830524031", "Brier Creek") for pid in pids]
    if llm_rows is None:
        llm_rows = [(pid, 8, 7) for pid in pids]

    db = MagicMock()
    db.execute.side_effect = [
        *_make_dist_results(pids, dist_values),
        _make_result(_school_agg_columns(), school_agg_rows),
        _make_result(_park_agg_columns(), park_agg_rows),
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
        db = _mock_db_queries(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert isinstance(result, pd.DataFrame)

    def test_index_is_property_id(self):
        db = _mock_db_queries(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert result.index.name == "property_id"
        assert list(result.index) == [1]

    def test_has_all_16_feature_columns(self):
        db = _mock_db_queries(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        assert list(result.columns) == FEATURE_COLUMNS
        assert len(result.columns) == 16

    def test_distance_features_populated(self):
        db = _mock_db_queries(pids=[1])
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
        db = _mock_db_queries(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["avg_school_rating_2mi"] == 7.5
        assert row["count_schools_2mi"] == 3

    def test_park_aggregate_features(self):
        db = _mock_db_queries(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["count_parks_2km"] == 4
        assert row["total_park_acres_2km"] == 120.5

    def test_containment_features(self):
        db = _mock_db_queries(pids=[1])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["census_tract_geoid"] == "37183052403"
        assert row["census_block_group_geoid"] == "371830524031"
        assert row["subdivision_name"] == "Brier Creek"

    def test_llm_score_features(self):
        db = _mock_db_queries(pids=[1])
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
        """When property_ids is None, should first load all IDs then query."""
        # First call returns the ID list, then 11 query results
        id_result = _make_result(["id"], [(1,)])
        db = MagicMock()
        db.execute.side_effect = [
            id_result,  # _get_all_property_ids
            *_make_dist_results([1]),
            _make_result(_school_agg_columns(), [(1, 7.5, 3)]),
            _make_result(_park_agg_columns(), [(1, 4, 120.5)]),
            _make_result(_contain_columns(), [(1, "37183052403", "371830524031", "Brier Creek")]),
            _make_result(_llm_columns(), [(1, 8, 7)]),
        ]
        result = build_geospatial_features(db, property_ids=None)
        assert len(result) == 1

    def test_multiple_properties(self):
        dist_values = {
            1: (100.0, 200.0, 300.0, 400.0, 150.0, 250.0, 3000.0),
            2: (110.0, 210.0, 310.0, 410.0, 160.0, 260.0, 3100.0),
        }
        school_agg_rows = [
            (1, 7.5, 3),
            (2, 8.0, 5),
        ]
        park_agg_rows = [
            (1, 4, 120.5),
            (2, 6, 200.0),
        ]
        contain_rows = [
            (1, "37183052403", "371830524031", "Brier Creek"),
            (2, "37183052404", "371830524041", None),
        ]
        llm_rows = [
            (1, 8, 7),
            (2, 6, 9),
        ]
        db = _mock_db_queries(
            pids=[1, 2],
            dist_values=dist_values,
            school_agg_rows=school_agg_rows,
            park_agg_rows=park_agg_rows,
            contain_rows=contain_rows,
            llm_rows=llm_rows,
        )
        result = build_geospatial_features(db, property_ids=[1, 2])
        assert len(result) == 2
        assert result.loc[2, "dist_nearest_school_m"] == 110.0
        assert result.loc[2, "subdivision_name"] is None

    def test_null_containment_values(self):
        """Properties outside all boundaries get None for containment."""
        db = _mock_db_queries(
            pids=[1],
            contain_rows=[(1, None, None, None)],
        )
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["census_tract_geoid"] is None
        assert row["census_block_group_geoid"] is None
        assert row["subdivision_name"] is None

    def test_null_llm_scores(self):
        """Properties without LLM scores get None."""
        db = _mock_db_queries(pids=[1], llm_rows=[(1, None, None)])
        result = build_geospatial_features(db, property_ids=[1])
        row = result.loc[1]
        assert row["llm_description_score"] is None
        assert row["llm_photo_score"] is None

    def test_batching_splits_large_lists(self):
        """Property lists > BATCH_SIZE are split into multiple batches."""
        ids = list(range(1, BATCH_SIZE + 52))  # 151 IDs -> 2 batches
        batch1 = ids[:BATCH_SIZE]
        batch2 = ids[BATCH_SIZE:]

        db = MagicMock()
        db.execute.side_effect = [
            # Batch 1: 7 distance + school_agg + park_agg + containment + llm = 11
            *_make_dist_results(batch1),
            _make_result(_school_agg_columns(), [(pid, 7.5, 3) for pid in batch1]),
            _make_result(_park_agg_columns(), [(pid, 4, 120.5) for pid in batch1]),
            _make_result(
                _contain_columns(), [(pid, "37183052403", "371830524031", "Test") for pid in batch1]
            ),
            _make_result(_llm_columns(), [(pid, 8, 7) for pid in batch1]),
            # Batch 2: same structure
            *_make_dist_results(batch2),
            _make_result(_school_agg_columns(), [(pid, 7.5, 3) for pid in batch2]),
            _make_result(_park_agg_columns(), [(pid, 4, 120.5) for pid in batch2]),
            _make_result(
                _contain_columns(), [(pid, "37183052403", "371830524031", "Test") for pid in batch2]
            ),
            _make_result(_llm_columns(), [(pid, 8, 7) for pid in batch2]),
        ]

        result = build_geospatial_features(db, property_ids=ids)
        assert len(result) == len(ids)
        assert db.execute.call_count == 22  # 11 queries * 2 batches

    def test_no_results_returns_empty(self):
        """When DB returns no rows, return empty DataFrame."""
        dist_names = [
            "dist_nearest_school_m",
            "dist_nearest_elementary_m",
            "dist_nearest_middle_m",
            "dist_nearest_high_m",
            "dist_nearest_park_m",
            "dist_nearest_greenway_m",
            "dist_nearest_hospital_m",
        ]

        db = MagicMock()
        db.execute.side_effect = [
            *[_make_result(["property_id", name], []) for name in dist_names],
            _make_result(_school_agg_columns(), []),
            _make_result(_park_agg_columns(), []),
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
        """There should be exactly 16 feature columns."""
        assert len(FEATURE_COLUMNS) == 16
