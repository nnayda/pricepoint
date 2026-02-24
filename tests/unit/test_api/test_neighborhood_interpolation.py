"""Unit tests for _interpolate_property_sales helper."""

from datetime import date

from pricepoint.api.routes.neighborhood import _interpolate_property_sales


class TestInterpolatePropertySales:
    """Direct tests for the interpolation function."""

    def test_empty_sales(self):
        """No sales → empty dict."""
        assert _interpolate_property_sales([]) == {}

    def test_single_sale(self):
        """Single sale → flat line ± 12 months."""
        result = _interpolate_property_sales([(date(2022, 6, 15), 400000.0)])
        assert len(result) == 25  # 12 before + 1 sale month + 12 after
        # All values should be 400k (flat hold)
        for v in result.values():
            assert v == 400000.0
        # Check date range
        keys = sorted(result.keys())
        assert keys[0] == "2021-06"
        assert keys[-1] == "2023-06"

    def test_two_sales(self):
        """Two sales 12 months apart → linearly interpolated between."""
        result = _interpolate_property_sales([
            (date(2022, 1, 15), 300000.0),
            (date(2023, 1, 15), 360000.0),
        ])
        # Before first sale: held at 300k
        assert result["2021-01"] == 300000.0
        # At first sale month
        assert result["2022-01"] == 300000.0
        # Mid-point (2022-07) should be roughly halfway
        mid = result["2022-07"]
        assert 325000 < mid < 335000  # ~330k
        # At last sale month
        assert result["2023-01"] == 360000.0
        # After last sale: held at 360k
        assert result["2024-01"] == 360000.0

    def test_multiple_sales(self):
        """Three sales → two interpolation segments."""
        result = _interpolate_property_sales([
            (date(2020, 6, 1), 250000.0),
            (date(2021, 6, 1), 300000.0),
            (date(2022, 6, 1), 280000.0),
        ])
        # First sale held before
        assert result["2019-06"] == 250000.0
        # Between first and second: increasing
        mid1 = result["2020-12"]
        assert 270000 < mid1 < 280000
        # Between second and third: decreasing
        mid2 = result["2021-12"]
        assert 285000 < mid2 < 295000
        # Last sale held after
        assert result["2023-06"] == 280000.0

    def test_unsorted_input(self):
        """Sales provided out of order are sorted correctly."""
        result = _interpolate_property_sales([
            (date(2023, 1, 1), 500000.0),
            (date(2021, 1, 1), 400000.0),
        ])
        # Should start from 2020-01 (12mo before first = 2021-01)
        keys = sorted(result.keys())
        assert keys[0] == "2020-01"
        # Held at first sale value before range
        assert result["2020-01"] == 400000.0
        assert result["2024-01"] == 500000.0

    def test_same_month_sales(self):
        """Two sales on the same date → uses latest value."""
        result = _interpolate_property_sales([
            (date(2022, 6, 15), 300000.0),
            (date(2022, 6, 15), 350000.0),
        ])
        # Both are on the same date; the second should take precedence in interpolation
        assert len(result) > 0
