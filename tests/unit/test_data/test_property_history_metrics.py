"""Tests for property_history_metrics computation module."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.housing.property_history_metrics import (
    MIN_SAMPLE_SIZE,
    SaleRecord,
    _compute_window,
    _fetch_sale_records,
    _month_range,
    build_property_history_metrics,
    verify_property_history_metrics,
)

# ---------------------------------------------------------------------------
# _month_range
# ---------------------------------------------------------------------------


class TestMonthRange:
    def test_single_month(self):
        result = _month_range(date(2024, 3, 15), date(2024, 3, 20))
        assert result == [date(2024, 3, 1)]

    def test_multiple_months(self):
        result = _month_range(date(2024, 1, 10), date(2024, 4, 5))
        assert result == [
            date(2024, 1, 1),
            date(2024, 2, 1),
            date(2024, 3, 1),
            date(2024, 4, 1),
        ]

    def test_year_boundary(self):
        result = _month_range(date(2023, 11, 1), date(2024, 2, 1))
        assert len(result) == 4
        assert result[0] == date(2023, 11, 1)
        assert result[-1] == date(2024, 2, 1)


# ---------------------------------------------------------------------------
# _compute_window
# ---------------------------------------------------------------------------


class TestComputeWindow:
    def _make_sales(self, n: int, base_price: float = 300000.0) -> list[SaleRecord]:
        """Create n sale records in January 2024."""
        return [
            SaleRecord(
                sold_date=date(2024, 1, d + 1),
                sold_price=base_price + i * 10000,
                days_on_market=10 + i,
            )
            for i, d in enumerate(range(n))
        ]

    def test_below_minimum_returns_none(self):
        sales = self._make_sales(MIN_SAMPLE_SIZE - 1)
        avg_dom, med_price, count = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert avg_dom is None
        assert med_price is None
        assert count == MIN_SAMPLE_SIZE - 1

    def test_exact_minimum_computes(self):
        sales = self._make_sales(MIN_SAMPLE_SIZE)
        avg_dom, med_price, count = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert avg_dom is not None
        assert med_price is not None
        assert count == MIN_SAMPLE_SIZE

    def test_avg_days_on_market(self):
        sales = [
            SaleRecord(date(2024, 1, 1), 100000, 10),
            SaleRecord(date(2024, 1, 2), 100000, 20),
            SaleRecord(date(2024, 1, 3), 100000, 30),
            SaleRecord(date(2024, 1, 4), 100000, 40),
            SaleRecord(date(2024, 1, 5), 100000, 50),
        ]
        avg_dom, _, _ = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert avg_dom == 30.0

    def test_median_sale_price_odd(self):
        sales = [
            SaleRecord(date(2024, 1, d + 1), price, 10)
            for d, price in enumerate([100000, 200000, 300000, 400000, 500000])
        ]
        _, med_price, _ = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert med_price == 300000.0

    def test_median_sale_price_even(self):
        sales = [
            SaleRecord(date(2024, 1, d + 1), price, 10)
            for d, price in enumerate([100000, 200000, 300000, 400000, 500000, 600000])
        ]
        _, med_price, _ = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert med_price == 350000.0

    def test_window_boundary_exclusive_end(self):
        """Sales on the end date should NOT be included."""
        sales = [SaleRecord(date(2024, 1, d + 1), 300000, 10) for d in range(5)] + [
            SaleRecord(date(2024, 2, 1), 999999, 10),  # on boundary
        ]
        _, _, count = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert count == 5

    def test_window_boundary_inclusive_start(self):
        """Sales on the start date should be included."""
        sales = [SaleRecord(date(2024, 1, 1), 300000 + i * 10000, 10) for i in range(5)]
        _, _, count = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert count == 5

    def test_empty_window(self):
        sales = [SaleRecord(date(2024, 3, 1), 300000, 10)]
        avg_dom, med_price, count = _compute_window(sales, date(2024, 1, 1), date(2024, 2, 1))
        assert avg_dom is None
        assert med_price is None
        assert count == 0


# ---------------------------------------------------------------------------
# _fetch_sale_records
# ---------------------------------------------------------------------------


class TestFetchSaleRecords:
    def test_filters_negative_dom(self):
        """Records where sold_date < contract_date should be excluded."""
        mock_session = MagicMock()
        mock_query = mock_session.query.return_value
        mock_join = mock_query.join.return_value
        mock_filter = mock_join.filter.return_value
        # Return a record where sold_date < contract_date
        mock_filter.all.return_value = [
            ("3700100", datetime(2024, 1, 1), 300000.0, datetime(2024, 1, 10)),
        ]

        result = _fetch_sale_records(mock_session)
        # DOM = (Jan 1 - Jan 10) = -9 days, should be filtered out
        assert result == {}

    def test_groups_by_township(self):
        mock_session = MagicMock()
        mock_query = mock_session.query.return_value
        mock_join = mock_query.join.return_value
        mock_filter = mock_join.filter.return_value
        mock_filter.all.return_value = [
            ("3700100", datetime(2024, 1, 10), 300000.0, datetime(2024, 1, 1)),
            ("3700100", datetime(2024, 2, 15), 310000.0, datetime(2024, 2, 1)),
            ("3700200", datetime(2024, 1, 20), 250000.0, datetime(2024, 1, 5)),
        ]

        result = _fetch_sale_records(mock_session)
        assert len(result) == 2
        assert len(result["3700100"]) == 2
        assert len(result["3700200"]) == 1


# ---------------------------------------------------------------------------
# build_property_history_metrics
# ---------------------------------------------------------------------------


class TestBuildPropertyHistoryMetrics:
    @patch("pricepoint.data.housing.property_history_metrics._fetch_sale_records")
    def test_returns_zero_when_no_data(self, mock_fetch):
        mock_fetch.return_value = {}
        session = MagicMock()
        result = build_property_history_metrics(session)
        assert result == 0

    @patch("pricepoint.data.housing.property_history_metrics.date")
    @patch("pricepoint.data.housing.property_history_metrics._fetch_sale_records")
    def test_builds_metrics_for_township(self, mock_fetch, mock_date):
        mock_date.today.return_value = date(2024, 4, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        # 6 sales in Jan 2024 for one township
        sales = [SaleRecord(date(2024, 1, d + 1), 300000.0 + d * 10000, 10 + d) for d in range(6)]
        mock_fetch.return_value = {"3700100": sales}

        session = MagicMock()
        added_rows = []
        session.add_all = lambda rows: added_rows.extend(rows)

        result = build_property_history_metrics(session)
        assert result > 0
        session.execute.assert_called_once()  # delete
        session.flush.assert_called_once()

    @patch("pricepoint.data.housing.property_history_metrics.date")
    @patch("pricepoint.data.housing.property_history_metrics._fetch_sale_records")
    def test_excludes_current_month(self, mock_fetch, mock_date):
        mock_date.today.return_value = date(2024, 2, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        sales = [SaleRecord(date(2024, 2, d + 1), 300000.0, 10) for d in range(6)]
        mock_fetch.return_value = {"3700100": sales}

        session = MagicMock()
        added_rows = []
        session.add_all = lambda rows: added_rows.extend(rows)

        build_property_history_metrics(session)
        # Feb 2024 is current month, should not appear as metric_month
        for row in added_rows:
            assert row.metric_month < date(2024, 2, 1)

    @patch("pricepoint.data.housing.property_history_metrics.date")
    @patch("pricepoint.data.housing.property_history_metrics._fetch_sale_records")
    def test_upsert_deletes_before_insert(self, mock_fetch, mock_date):
        mock_date.today.return_value = date(2024, 3, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        sales = [SaleRecord(date(2024, 1, d + 1), 300000.0, 10) for d in range(6)]
        mock_fetch.return_value = {"3700100": sales}

        session = MagicMock()
        session.add_all = MagicMock()

        build_property_history_metrics(session)

        # Should have called delete before add_all
        session.execute.assert_called_once()
        session.add_all.assert_called_once()


# ---------------------------------------------------------------------------
# verify_property_history_metrics
# ---------------------------------------------------------------------------


class TestVerifyPropertyHistoryMetrics:
    def test_raises_when_empty(self):
        session = MagicMock()
        session.query.return_value.count.return_value = 0
        session.query.return_value.distinct.return_value.count.return_value = 0
        session.query.return_value.filter.return_value.count.return_value = 0

        with pytest.raises(RuntimeError, match="empty"):
            verify_property_history_metrics(session)

    def test_returns_stats(self):
        session = MagicMock()
        session.query.return_value.count.return_value = 100
        session.query.return_value.distinct.return_value.count.return_value = 5
        session.query.return_value.filter.return_value.count.return_value = 80

        stats = verify_property_history_metrics(session)
        assert stats["total_rows"] == 100
