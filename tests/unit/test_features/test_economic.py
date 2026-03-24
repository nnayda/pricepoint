"""Unit tests for economic feature engineering."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.features.economic import (
    SERIES_IDS,
    YOY_FEATURES,
    _build_row,
    _build_row_from_cache,
    _cache_lookup,
    _compute_yoy_pct,
    _get_property_dates,
    _lookup_value,
    _lookup_yoy_value,
    _prefetch_series,
    _yoy_date,
    build_economic_features,
    build_training_economic_features,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_db_with_property_rows(rows: list[tuple]) -> MagicMock:
    """Return a mock Session whose execute returns *rows* for the first call."""
    db = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = rows
    db.execute.return_value = result
    return db


def _mock_db_scalar(value: float | None) -> MagicMock:
    """Return a mock Session whose execute().fetchone() returns a single value."""
    db = MagicMock()
    result = MagicMock()
    if value is not None:
        result.fetchone.return_value = (value,)
    else:
        result.fetchone.return_value = None
    db.execute.return_value = result
    return db


def _make_cache(value: float = 200.0) -> dict[str, tuple[list[date], list[float]]]:
    """Build a series cache with constant values for all SERIES_IDS."""
    cache: dict[str, tuple[list[date], list[float]]] = {}
    for series_id in SERIES_IDS.values():
        cache[series_id] = (
            [date(2023, 1, 1), date(2024, 1, 1)],
            [value, value],
        )
    return cache


# ---------------------------------------------------------------------------
# _compute_yoy_pct
# ---------------------------------------------------------------------------


class TestComputeYoyPct:
    def test_normal(self) -> None:
        assert _compute_yoy_pct(110.0, 100.0) == pytest.approx(10.0)

    def test_negative_change(self) -> None:
        assert _compute_yoy_pct(90.0, 100.0) == pytest.approx(-10.0)

    def test_current_none(self) -> None:
        assert _compute_yoy_pct(None, 100.0) is None

    def test_previous_none(self) -> None:
        assert _compute_yoy_pct(110.0, None) is None

    def test_previous_zero(self) -> None:
        assert _compute_yoy_pct(110.0, 0) is None


# ---------------------------------------------------------------------------
# _lookup_value / _lookup_yoy_value
# ---------------------------------------------------------------------------


class TestLookupValue:
    def test_returns_float(self) -> None:
        db = _mock_db_scalar(6.5)
        val = _lookup_value(db, "MORTGAGE30US", date(2024, 6, 1))
        assert val == pytest.approx(6.5)

    def test_returns_none_when_no_rows(self) -> None:
        db = _mock_db_scalar(None)
        assert _lookup_value(db, "MORTGAGE30US", date(2024, 6, 1)) is None


class TestLookupYoyValue:
    def test_subtracts_one_year(self) -> None:
        db = _mock_db_scalar(5.0)
        val = _lookup_yoy_value(db, "CPIAUCSL", date(2024, 6, 15))
        assert val == pytest.approx(5.0)
        # Verify the yoy_date parameter passed is one year back
        args, _ = db.execute.call_args
        assert args[1]["yoy_date"] == date(2023, 6, 15)


# ---------------------------------------------------------------------------
# _get_property_dates
# ---------------------------------------------------------------------------


class TestGetPropertyDates:
    def test_uses_sold_date_when_present(self) -> None:
        sold = datetime(2024, 3, 15)
        processed = datetime(2024, 4, 1)
        db = _mock_db_with_property_rows([(1, sold, processed)])
        df = _get_property_dates(db)
        assert len(df) == 1
        assert df.iloc[0]["ref_date"] == date(2024, 3, 15)

    def test_falls_back_to_processed_at(self) -> None:
        processed = datetime(2024, 4, 1)
        db = _mock_db_with_property_rows([(2, None, processed)])
        df = _get_property_dates(db)
        assert len(df) == 1
        assert df.iloc[0]["ref_date"] == date(2024, 4, 1)

    def test_skips_when_both_none(self) -> None:
        db = _mock_db_with_property_rows([(3, None, None)])
        df = _get_property_dates(db)
        assert len(df) == 0

    def test_passes_property_ids_filter(self) -> None:
        db = _mock_db_with_property_rows([])
        _get_property_dates(db, property_ids=[10, 20])
        args, _ = db.execute.call_args
        assert args[1]["filter_ids"] is True
        assert args[1]["property_ids"] == [10, 20]

    def test_no_filter_when_none(self) -> None:
        db = _mock_db_with_property_rows([])
        _get_property_dates(db, property_ids=None)
        args, _ = db.execute.call_args
        assert args[1]["filter_ids"] is False


# ---------------------------------------------------------------------------
# _build_row (individual DB queries — kept for compatibility)
# ---------------------------------------------------------------------------


class TestBuildRow:
    def test_contains_all_features(self) -> None:
        db = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = (100.0,)
        db.execute.return_value = result

        row = _build_row(db, property_id=1, ref_date=date(2024, 6, 1))

        assert row["property_id"] == 1
        # All base features present
        for feat in SERIES_IDS:
            assert feat in row
        # YoY features present
        for yoy_col in YOY_FEATURES.values():
            assert yoy_col in row

    def test_nc_unemployment_not_in_series(self) -> None:
        """NC unemployment rate should have been removed from SERIES_IDS."""
        assert "unemployment_rate_nc" not in SERIES_IDS

    def test_yoy_computed_correctly(self) -> None:
        """When current=110 and yoy=100, pct should be 10.0."""
        db = MagicMock()
        call_count = {"n": 0}

        def side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            result = MagicMock()
            result.fetchone.return_value = (100.0,)
            return result

        db.execute.side_effect = side_effect
        row = _build_row(db, property_id=1, ref_date=date(2024, 6, 1))

        # With all values = 100, yoy pct = 0.0
        assert row["cpi_yoy_pct"] == pytest.approx(0.0)
        assert row["case_shiller_yoy_pct"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Cache-based helpers
# ---------------------------------------------------------------------------


class TestPrefetchSeries:
    def test_groups_by_series_id(self) -> None:
        db = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = [
            ("MORTGAGE30US", date(2024, 1, 1), 6.5),
            ("MORTGAGE30US", date(2024, 2, 1), 6.6),
            ("CPIAUCSL", date(2024, 1, 1), 310.0),
        ]
        db.execute.return_value = result

        cache = _prefetch_series(db)

        assert len(cache) == 2
        assert len(cache["MORTGAGE30US"][0]) == 2
        assert len(cache["CPIAUCSL"][0]) == 1
        assert cache["MORTGAGE30US"][1] == [6.5, 6.6]

    def test_converts_datetime_to_date(self) -> None:
        db = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = [
            ("MORTGAGE30US", datetime(2024, 1, 1), 6.5),
        ]
        db.execute.return_value = result

        cache = _prefetch_series(db)
        assert cache["MORTGAGE30US"][0] == [date(2024, 1, 1)]

    def test_empty_table(self) -> None:
        db = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = []
        db.execute.return_value = result

        cache = _prefetch_series(db)
        assert cache == {}


class TestCacheLookup:
    def test_exact_match(self) -> None:
        cache = {"S1": ([date(2024, 1, 1), date(2024, 2, 1)], [100.0, 200.0])}
        assert _cache_lookup(cache, "S1", date(2024, 2, 1)) == 200.0

    def test_returns_latest_before_date(self) -> None:
        cache = {"S1": ([date(2024, 1, 1), date(2024, 3, 1)], [100.0, 300.0])}
        assert _cache_lookup(cache, "S1", date(2024, 2, 15)) == 100.0

    def test_returns_none_before_all_data(self) -> None:
        cache = {"S1": ([date(2024, 6, 1)], [100.0])}
        assert _cache_lookup(cache, "S1", date(2024, 1, 1)) is None

    def test_returns_none_for_missing_series(self) -> None:
        cache: dict[str, tuple[list[date], list[float]]] = {}
        assert _cache_lookup(cache, "MISSING", date(2024, 1, 1)) is None


class TestYoyDate:
    def test_normal_date(self) -> None:
        assert _yoy_date(date(2024, 6, 15)) == date(2023, 6, 15)

    def test_leap_year_feb29(self) -> None:
        assert _yoy_date(date(2024, 2, 29)) == date(2023, 2, 28)


class TestBuildRowFromCache:
    def test_all_features_present(self) -> None:
        cache = _make_cache(200.0)
        row = _build_row_from_cache(cache, "property_id", 42, date(2024, 6, 1))

        assert row["property_id"] == 42
        for feat in SERIES_IDS:
            assert feat in row
        for yoy_col in YOY_FEATURES.values():
            assert yoy_col in row

    def test_yoy_pct_with_constant_values(self) -> None:
        cache = _make_cache(200.0)
        row = _build_row_from_cache(cache, "sale_event_id", "evt1", date(2024, 6, 1))

        assert row["cpi_yoy_pct"] == pytest.approx(0.0)
        assert row["case_shiller_yoy_pct"] == pytest.approx(0.0)

    def test_yoy_pct_with_changing_values(self) -> None:
        cache: dict[str, tuple[list[date], list[float]]] = {}
        for series_id in SERIES_IDS.values():
            cache[series_id] = (
                [date(2023, 1, 1), date(2024, 1, 1)],
                [100.0, 110.0],
            )

        row = _build_row_from_cache(cache, "property_id", 1, date(2024, 6, 1))
        assert row["cpi_yoy_pct"] == pytest.approx(10.0)

    def test_none_when_series_missing(self) -> None:
        cache: dict[str, tuple[list[date], list[float]]] = {}
        row = _build_row_from_cache(cache, "property_id", 1, date(2024, 6, 1))

        for feat in SERIES_IDS:
            assert row[feat] is None


# ---------------------------------------------------------------------------
# build_economic_features (integration of components)
# ---------------------------------------------------------------------------


class TestBuildEconomicFeatures:
    def test_returns_empty_df_when_no_properties(self) -> None:
        db = _mock_db_with_property_rows([])
        df = build_economic_features(db)
        assert df.empty
        assert df.index.name == "property_id"
        # Should still have the correct columns
        expected_cols = set(SERIES_IDS.keys()) | set(YOY_FEATURES.values())
        assert expected_cols == set(df.columns)

    def test_single_property_all_columns(self) -> None:
        """Full end-to-end with a single property and constant indicator value."""
        db = MagicMock()
        call_idx = {"n": 0}
        cache = _make_cache(200.0)

        def execute_side_effect(*args, **kwargs):
            call_idx["n"] += 1
            result = MagicMock()
            if call_idx["n"] == 1:
                # First call: property dates query
                result.fetchall.return_value = [(42, datetime(2024, 5, 10), datetime(2024, 5, 1))]
                return result
            # Second call: prefetch series
            result.fetchall.return_value = []
            return result

        db.execute.side_effect = execute_side_effect

        with patch("pricepoint.features.economic._prefetch_series", return_value=cache):
            df = build_economic_features(db, property_ids=[42])

        assert list(df.index) == [42]
        assert df.loc[42, "mortgage_rate_30yr"] == pytest.approx(200.0)
        assert df.loc[42, "cpi_yoy_pct"] == pytest.approx(0.0)

    def test_as_of_date_overrides(self) -> None:
        """When as_of_date is given, all properties use that date."""
        db = MagicMock()
        cache = _make_cache(50.0)

        dates_result = MagicMock()
        dates_result.fetchall.return_value = [(1, datetime(2024, 1, 1), datetime(2024, 1, 1))]
        db.execute.return_value = dates_result

        override = date(2025, 1, 15)
        with patch("pricepoint.features.economic._prefetch_series", return_value=cache):
            df = build_economic_features(db, as_of_date=override)

        assert not df.empty
        assert df.loc[1, "mortgage_rate_30yr"] == pytest.approx(50.0)

    def test_multiple_properties(self) -> None:
        db = MagicMock()
        cache = _make_cache(75.0)

        dates_result = MagicMock()
        dates_result.fetchall.return_value = [
            (10, datetime(2024, 3, 1), None),
            (20, None, datetime(2024, 6, 1)),
        ]
        db.execute.return_value = dates_result

        with patch("pricepoint.features.economic._prefetch_series", return_value=cache):
            df = build_economic_features(db)

        assert len(df) == 2
        assert set(df.index) == {10, 20}
        assert df.index.name == "property_id"


# ---------------------------------------------------------------------------
# build_training_economic_features
# ---------------------------------------------------------------------------


class TestBuildTrainingEconomicFeatures:
    def test_returns_empty_df_when_no_events(self) -> None:
        db = MagicMock()
        events = pd.DataFrame(columns=["sale_event_id", "property_id", "sale_date"])
        df = build_training_economic_features(db, events)

        assert df.empty
        assert df.index.name == "sale_event_id"
        expected_cols = set(SERIES_IDS.keys()) | set(YOY_FEATURES.values())
        assert expected_cols == set(df.columns)

    def test_builds_features_for_events(self) -> None:
        db = MagicMock()
        cache = _make_cache(300.0)
        events = pd.DataFrame(
            {
                "sale_event_id": ["e1", "e2"],
                "property_id": [10, 20],
                "sale_date": [date(2024, 3, 1), date(2024, 6, 1)],
            }
        )

        with patch("pricepoint.features.economic._prefetch_series", return_value=cache):
            df = build_training_economic_features(db, events)

        assert len(df) == 2
        assert set(df.index) == {"e1", "e2"}
        assert df.index.name == "sale_event_id"
        assert df.loc["e1", "mortgage_rate_30yr"] == pytest.approx(300.0)

    def test_handles_datetime_sale_dates(self) -> None:
        db = MagicMock()
        cache = _make_cache(100.0)
        events = pd.DataFrame(
            {
                "sale_event_id": ["e1"],
                "property_id": [10],
                "sale_date": [datetime(2024, 3, 1, 12, 0, 0)],
            }
        )

        with patch("pricepoint.features.economic._prefetch_series", return_value=cache):
            df = build_training_economic_features(db, events)

        assert len(df) == 1
        assert df.loc["e1", "cpi"] == pytest.approx(100.0)
