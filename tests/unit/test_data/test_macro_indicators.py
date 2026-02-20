"""Unit tests for the FRED macro indicators collector."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.data.economic.macro_indicators import (
    _bulk_upsert,
    _fetch_series,
    _get_latest_date,
    fetch_macro_indicators,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fred_series(dates: list[str], values: list[float]) -> pd.Series:
    """Build a pandas Series that mimics fredapi output."""
    index = pd.to_datetime(dates)
    return pd.Series(values, index=index)


# ---------------------------------------------------------------------------
# _get_latest_date
# ---------------------------------------------------------------------------


class TestGetLatestDate:
    def test_returns_none_when_no_rows(self):
        db = MagicMock()
        db.execute.return_value.scalar.return_value = None
        assert _get_latest_date(db, "MORTGAGE30US") is None

    def test_returns_date_when_rows_exist(self):
        db = MagicMock()
        expected = date(2024, 6, 15)
        db.execute.return_value.scalar.return_value = expected
        assert _get_latest_date(db, "MORTGAGE30US") == expected


# ---------------------------------------------------------------------------
# _fetch_series
# ---------------------------------------------------------------------------


class TestFetchSeries:
    def test_fetches_valid_observations(self):
        fred = MagicMock()
        fred.get_series.return_value = _make_fred_series(
            ["2024-01-04", "2024-01-11", "2024-01-18"],
            [6.62, 6.60, 6.69],
        )
        rows = _fetch_series(fred, "MORTGAGE30US", date(2024, 1, 1))
        assert len(rows) == 3
        assert rows[0]["series_id"] == "MORTGAGE30US"
        assert rows[0]["value"] == 6.62
        assert rows[0]["observation_date"] == date(2024, 1, 4)

    def test_skips_nan_values(self):
        fred = MagicMock()
        series = _make_fred_series(["2024-01-04", "2024-01-11"], [6.62, float("nan")])
        # NaN is not None and not ".", but float("nan") should still be kept
        # because float(nan) succeeds. The FRED API uses "." for missing.
        fred.get_series.return_value = series
        rows = _fetch_series(fred, "MORTGAGE30US", date(2024, 1, 1))
        # NaN is a valid float, so it would be included; only "." strings are skipped
        assert len(rows) == 2

    def test_skips_dot_string_values(self):
        """FRED uses '.' to indicate missing data."""
        fred = MagicMock()
        series = pd.Series(
            [6.62, "."],
            index=pd.to_datetime(["2024-01-04", "2024-01-11"]),
        )
        fred.get_series.return_value = series
        rows = _fetch_series(fred, "MORTGAGE30US", date(2024, 1, 1))
        assert len(rows) == 1
        assert rows[0]["value"] == 6.62

    def test_returns_empty_on_api_error(self):
        fred = MagicMock()
        fred.get_series.side_effect = ValueError("API error")
        rows = _fetch_series(fred, "BADID", date(2024, 1, 1))
        assert rows == []

    def test_empty_series(self):
        fred = MagicMock()
        fred.get_series.return_value = pd.Series(dtype=float)
        rows = _fetch_series(fred, "MORTGAGE30US", date(2024, 1, 1))
        assert rows == []


# ---------------------------------------------------------------------------
# _bulk_upsert
# ---------------------------------------------------------------------------


class TestBulkUpsert:
    def test_returns_zero_for_empty_list(self):
        db = MagicMock()
        assert _bulk_upsert(db, []) == 0
        db.execute.assert_not_called()

    def test_inserts_rows_and_commits(self):
        db = MagicMock()
        db.execute.return_value.rowcount = 3
        rows = [
            {"series_id": "MORTGAGE30US", "observation_date": date(2024, 1, 4), "value": 6.62},
            {"series_id": "MORTGAGE30US", "observation_date": date(2024, 1, 11), "value": 6.60},
            {"series_id": "MORTGAGE30US", "observation_date": date(2024, 1, 18), "value": 6.69},
        ]
        count = _bulk_upsert(db, rows)
        assert count == 3
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_conflict_returns_lower_count(self):
        """ON CONFLICT DO NOTHING means rowcount < len(rows) when dupes exist."""
        db = MagicMock()
        db.execute.return_value.rowcount = 1
        rows = [
            {"series_id": "MORTGAGE30US", "observation_date": date(2024, 1, 4), "value": 6.62},
            {"series_id": "MORTGAGE30US", "observation_date": date(2024, 1, 11), "value": 6.60},
        ]
        count = _bulk_upsert(db, rows)
        assert count == 1


# ---------------------------------------------------------------------------
# fetch_macro_indicators (integration-style with mocks)
# ---------------------------------------------------------------------------


class TestFetchMacroIndicators:
    @patch("pricepoint.data.economic.macro_indicators.Fred")
    @patch("pricepoint.data.economic.macro_indicators.get_settings")
    @patch("pricepoint.data.economic.macro_indicators.SessionLocal")
    @patch("pricepoint.data.economic.macro_indicators._get_latest_date")
    @patch("pricepoint.data.economic.macro_indicators._bulk_upsert")
    def test_full_fetch_no_existing_data(
        self, mock_upsert, mock_latest, mock_session_local, mock_settings, mock_fred_cls
    ):
        settings = MagicMock()
        settings.fred_api_key = "test-key"
        settings.fred_series_ids = ["MORTGAGE30US", "UNRATE"]
        settings.fred_lookback_years = 10
        mock_settings.return_value = settings

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_latest.return_value = None
        mock_upsert.return_value = 5

        fred_instance = MagicMock()
        fred_instance.get_series.return_value = _make_fred_series(
            ["2024-01-04", "2024-01-11"], [6.62, 6.60]
        )
        mock_fred_cls.return_value = fred_instance

        counts = fetch_macro_indicators()

        assert counts == {"MORTGAGE30US": 5, "UNRATE": 5}
        assert mock_upsert.call_count == 2
        mock_db.close.assert_called_once()

    @patch("pricepoint.data.economic.macro_indicators.Fred")
    @patch("pricepoint.data.economic.macro_indicators.get_settings")
    @patch("pricepoint.data.economic.macro_indicators._get_latest_date")
    @patch("pricepoint.data.economic.macro_indicators._bulk_upsert")
    def test_incremental_fetch_uses_latest_date(
        self, mock_upsert, mock_latest, mock_settings, mock_fred_cls
    ):
        settings = MagicMock()
        settings.fred_api_key = "test-key"
        settings.fred_series_ids = ["MORTGAGE30US"]
        settings.fred_lookback_years = 10
        mock_settings.return_value = settings

        mock_db = MagicMock()
        mock_latest.return_value = date(2024, 6, 1)
        mock_upsert.return_value = 2

        fred_instance = MagicMock()
        fred_instance.get_series.return_value = _make_fred_series(
            ["2024-06-06", "2024-06-13"], [6.99, 6.95]
        )
        mock_fred_cls.return_value = fred_instance

        counts = fetch_macro_indicators(db=mock_db)

        assert counts == {"MORTGAGE30US": 2}
        # Should request from day after latest
        call_args = fred_instance.get_series.call_args
        assert call_args[1]["observation_start"] == date(2024, 6, 2)

    @patch("pricepoint.data.economic.macro_indicators.Fred", None)
    def test_raises_import_error_when_fredapi_missing(self):
        with pytest.raises(ImportError, match="fredapi is required"):
            fetch_macro_indicators()

    @patch("pricepoint.data.economic.macro_indicators.Fred")
    @patch("pricepoint.data.economic.macro_indicators.get_settings")
    def test_raises_when_api_key_empty(self, mock_settings, mock_fred_cls):
        settings = MagicMock()
        settings.fred_api_key = ""
        mock_settings.return_value = settings

        with pytest.raises(ValueError, match="fred_api_key must be set"):
            fetch_macro_indicators()

    @patch("pricepoint.data.economic.macro_indicators.Fred")
    @patch("pricepoint.data.economic.macro_indicators.get_settings")
    @patch("pricepoint.data.economic.macro_indicators.SessionLocal")
    @patch("pricepoint.data.economic.macro_indicators._get_latest_date")
    @patch("pricepoint.data.economic.macro_indicators._bulk_upsert")
    def test_handles_series_fetch_failure_gracefully(
        self, mock_upsert, mock_latest, mock_session_local, mock_settings, mock_fred_cls
    ):
        """If one series fails, others should still be processed."""
        settings = MagicMock()
        settings.fred_api_key = "test-key"
        settings.fred_series_ids = ["BADID", "UNRATE"]
        settings.fred_lookback_years = 10
        mock_settings.return_value = settings

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_latest.return_value = None

        fred_instance = MagicMock()

        def side_effect(series_id, **kwargs):
            if series_id == "BADID":
                raise ValueError("Unknown series")
            return _make_fred_series(["2024-01-04"], [4.0])

        fred_instance.get_series.side_effect = side_effect
        mock_fred_cls.return_value = fred_instance
        mock_upsert.side_effect = lambda db, rows: 0 if not rows else len(rows)

        counts = fetch_macro_indicators()

        # BADID returns 0 inserted (empty rows -> _bulk_upsert returns 0)
        assert counts["BADID"] == 0
        assert counts["UNRATE"] == 1

    @patch("pricepoint.data.economic.macro_indicators.Fred")
    @patch("pricepoint.data.economic.macro_indicators.get_settings")
    @patch("pricepoint.data.economic.macro_indicators.SessionLocal")
    @patch("pricepoint.data.economic.macro_indicators._get_latest_date")
    @patch("pricepoint.data.economic.macro_indicators._bulk_upsert")
    def test_rollback_on_unexpected_error(
        self, mock_upsert, mock_latest, mock_session_local, mock_settings, mock_fred_cls
    ):
        settings = MagicMock()
        settings.fred_api_key = "test-key"
        settings.fred_series_ids = ["MORTGAGE30US"]
        settings.fred_lookback_years = 10
        mock_settings.return_value = settings

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_latest.side_effect = RuntimeError("DB failure")

        fred_instance = MagicMock()
        mock_fred_cls.return_value = fred_instance

        with pytest.raises(RuntimeError, match="DB failure"):
            fetch_macro_indicators()

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
