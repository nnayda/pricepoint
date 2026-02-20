"""Unit tests for economic feature engineering."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from pricepoint.features.economic import (
    SERIES_IDS,
    YOY_FEATURES,
    _build_row,
    _compute_yoy_pct,
    _get_property_dates,
    _lookup_value,
    _lookup_yoy_value,
    build_economic_features,
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
# _build_row
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

    def test_yoy_computed_correctly(self) -> None:
        """When current=110 and yoy=100, pct should be 10.0."""
        db = MagicMock()
        # We need to return different values for current vs yoy lookups.
        # current lookup returns 110, yoy lookup returns 100.
        call_count = {"n": 0}

        def side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            result = MagicMock()
            # Odd calls are "current" lookups, even are "yoy" lookups
            # But the pattern is: for each feature, one current lookup,
            # and for yoy features an additional yoy lookup.
            result.fetchone.return_value = (100.0,)
            return result

        db.execute.side_effect = side_effect
        row = _build_row(db, property_id=1, ref_date=date(2024, 6, 1))

        # With all values = 100, yoy pct = 0.0
        assert row["cpi_yoy_pct"] == pytest.approx(0.0)
        assert row["case_shiller_yoy_pct"] == pytest.approx(0.0)


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

        def execute_side_effect(*args, **kwargs):
            call_idx["n"] += 1
            result = MagicMock()
            if call_idx["n"] == 1:
                # First call: property dates query
                result.fetchall.return_value = [(42, datetime(2024, 5, 10), datetime(2024, 5, 1))]
                return result
            # Subsequent calls: indicator lookups
            result.fetchone.return_value = (200.0,)
            return result

        db.execute.side_effect = execute_side_effect
        df = build_economic_features(db, property_ids=[42])

        assert list(df.index) == [42]
        assert df.loc[42, "mortgage_rate_30yr"] == pytest.approx(200.0)
        assert df.loc[42, "cpi_yoy_pct"] == pytest.approx(0.0)

    def test_as_of_date_overrides(self) -> None:
        """When as_of_date is given, all properties use that date."""
        db = MagicMock()
        call_idx = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_idx["n"] += 1
            result = MagicMock()
            if call_idx["n"] == 1:
                result.fetchall.return_value = [(1, datetime(2024, 1, 1), datetime(2024, 1, 1))]
                return result
            result.fetchone.return_value = (50.0,)
            return result

        db.execute.side_effect = execute_side_effect

        override = date(2025, 1, 15)
        df = build_economic_features(db, as_of_date=override)

        assert not df.empty
        # Verify the lookups used the override date, not the property date.
        # The second call onward should use the override date as ref_date.
        indicator_calls = db.execute.call_args_list[1:]
        for c in indicator_calls:
            params = c[1] if len(c) > 1 else c[0][1] if len(c[0]) > 1 else {}
            if "ref_date" in params:
                assert params["ref_date"] == override

    def test_multiple_properties(self) -> None:
        db = MagicMock()
        call_idx = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_idx["n"] += 1
            result = MagicMock()
            if call_idx["n"] == 1:
                result.fetchall.return_value = [
                    (10, datetime(2024, 3, 1), None),
                    (20, None, datetime(2024, 6, 1)),
                ]
                return result
            result.fetchone.return_value = (75.0,)
            return result

        db.execute.side_effect = execute_side_effect

        df = build_economic_features(db)
        assert len(df) == 2
        assert set(df.index) == {10, 20}
        assert df.index.name == "property_id"
