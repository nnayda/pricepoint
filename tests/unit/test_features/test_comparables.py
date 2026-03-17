"""Tests for comparable sales feature engineering."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pricepoint.features.comparables import (
    _CHUNK_SIZE,
    FEATURE_COLUMNS,
    _compute_derived,
    build_comparable_features,
)


@pytest.fixture()
def mock_db():
    """Create a mock database session."""
    return MagicMock()


def _make_raw_df(
    property_ids: list[int],
    *,
    comp_counts: list[int] | None = None,
    median_ppsfs: list[float | None] | None = None,
    adjusted_prices: list[float | None] | None = None,
    nearest_prices: list[float | None] | None = None,
    subject_ppsfs: list[float | None] | None = None,
    price_spreads: list[float | None] | None = None,
    avg_days: list[float | None] | None = None,
    nearest_dists: list[float | None] | None = None,
) -> pd.DataFrame:
    """Create a raw DataFrame as returned by the SQL query (pre-derived)."""
    n = len(property_ids)
    return pd.DataFrame(
        {
            "property_id": property_ids,
            "comp_count": comp_counts or [5] * n,
            "comp_median_ppsf": median_ppsfs or [200.0] * n,
            "comp_mean_adjusted_price": adjusted_prices or [400000.0] * n,
            "comp_nearest_price": nearest_prices or [380000.0] * n,
            "subject_ppsf": subject_ppsfs or [210.0] * n,
            "comp_price_spread": price_spreads or [50000.0] * n,
            "comp_avg_days_ago": avg_days or [90.0] * n,
            "comp_nearest_distance_m": nearest_dists or [500.0] * n,
        }
    )


class TestBuildComparableFeatures:
    """Tests for the main build_comparable_features function."""

    def test_returns_expected_columns(self, mock_db):
        """Result DataFrame should contain all 8 feature columns."""
        raw = _make_raw_df([1, 2])
        with patch("pricepoint.features.comparables._exec_query", return_value=raw):
            result = build_comparable_features(mock_db, property_ids=[1, 2])

        assert list(result.columns) == FEATURE_COLUMNS
        assert len(result) == 2

    def test_empty_when_no_properties(self, mock_db):
        """Empty property_ids list returns empty DataFrame."""
        result = build_comparable_features(mock_db, property_ids=[])

        assert result.empty
        assert list(result.columns) == FEATURE_COLUMNS

    def test_empty_when_query_returns_no_rows(self, mock_db):
        """If the SQL query returns no rows, return empty DataFrame."""
        empty = pd.DataFrame(
            columns=[
                "property_id",
                "comp_count",
                "comp_median_ppsf",
                "comp_mean_adjusted_price",
                "comp_nearest_price",
                "subject_ppsf",
                "comp_price_spread",
                "comp_avg_days_ago",
                "comp_nearest_distance_m",
            ]
        )
        with patch("pricepoint.features.comparables._exec_query", return_value=empty):
            result = build_comparable_features(mock_db, property_ids=[1])

        assert result.empty

    def test_passes_property_ids_to_query(self, mock_db):
        """property_ids should be forwarded as SQL parameters."""
        raw = _make_raw_df([42])
        with patch("pricepoint.features.comparables._exec_query", return_value=raw) as mock_exec:
            build_comparable_features(mock_db, property_ids=[42])

        args = mock_exec.call_args
        assert args[0][2] == {"property_ids": [42]}

    def test_chunks_large_batches(self, mock_db):
        """Batches larger than _CHUNK_SIZE should be split into chunks."""
        large_ids = list(range(1, _CHUNK_SIZE + 100))
        raw1 = _make_raw_df(list(range(1, _CHUNK_SIZE + 1)))
        raw2 = _make_raw_df(list(range(_CHUNK_SIZE + 1, _CHUNK_SIZE + 100)))

        with patch(
            "pricepoint.features.comparables._exec_query",
            side_effect=[raw1, raw2],
        ):
            result = build_comparable_features(mock_db, property_ids=large_ids)

        assert len(result) == len(large_ids)


class TestComputeDerived:
    """Tests for the _compute_derived post-processing function."""

    def test_ppsf_ratio_calculation(self):
        """comp_ppsf_ratio = subject_ppsf / comp_median_ppsf."""
        df = _make_raw_df([1], subject_ppsfs=[210.0], median_ppsfs=[200.0])
        result = _compute_derived(df)

        assert result.loc[0, "comp_ppsf_ratio"] == pytest.approx(1.05)

    def test_ppsf_ratio_null_when_no_comps(self):
        """comp_ppsf_ratio is NULL when comp_median_ppsf is NULL."""
        df = _make_raw_df([1], subject_ppsfs=[210.0], median_ppsfs=[None])
        result = _compute_derived(df)

        assert pd.isna(result.loc[0, "comp_ppsf_ratio"])

    def test_ppsf_ratio_null_when_no_subject_ppsf(self):
        """comp_ppsf_ratio is NULL when subject has no price_per_sqft."""
        df = _make_raw_df([1], subject_ppsfs=[None], median_ppsfs=[200.0])
        result = _compute_derived(df)

        assert pd.isna(result.loc[0, "comp_ppsf_ratio"])

    def test_comp_count_zero_when_no_comps(self):
        """comp_count should be 0 (not NULL) when LEFT JOIN finds no comps."""
        df = _make_raw_df(
            [1],
            comp_counts=[None],
            median_ppsfs=[None],
            adjusted_prices=[None],
            nearest_prices=[None],
            price_spreads=[None],
            avg_days=[None],
            nearest_dists=[None],
        )
        result = _compute_derived(df)

        assert result.loc[0, "comp_count"] == 0

    def test_median_ppsf_calculation(self):
        """comp_median_ppsf should be passed through from SQL."""
        df = _make_raw_df([1], median_ppsfs=[175.5])
        result = _compute_derived(df)

        assert result.loc[0, "comp_median_ppsf"] == pytest.approx(175.5)

    def test_mean_adjusted_price_calculation(self):
        """comp_mean_adjusted_price should be passed through from SQL."""
        df = _make_raw_df([1], adjusted_prices=[425000.0])
        result = _compute_derived(df)

        assert result.loc[0, "comp_mean_adjusted_price"] == pytest.approx(425000.0)

    def test_nearest_price_is_spatially_closest(self):
        """comp_nearest_price should reflect the nearest comp's sold price."""
        df = _make_raw_df([1], nearest_prices=[350000.0])
        result = _compute_derived(df)

        assert result.loc[0, "comp_nearest_price"] == pytest.approx(350000.0)

    def test_drops_subject_ppsf_column(self):
        """The helper column subject_ppsf should be dropped from output."""
        df = _make_raw_df([1])
        result = _compute_derived(df)

        assert "subject_ppsf" not in result.columns

    def test_empty_dataframe(self):
        """_compute_derived handles empty DataFrame gracefully."""
        df = pd.DataFrame()
        result = _compute_derived(df)

        assert result.empty


class TestTemporalLeakage:
    """Tests verifying temporal leakage prevention in the SQL query."""

    def test_sql_contains_temporal_filter(self):
        """The SQL query must include a temporal leakage guard."""
        from pricepoint.features.comparables import _COMP_FEATURES_SQL

        assert "c.sold_date < s.sold_date" in _COMP_FEATURES_SQL

    def test_sql_allows_null_sold_date(self):
        """Properties without sold_date (active listings) should use all comps."""
        from pricepoint.features.comparables import _COMP_FEATURES_SQL

        assert "s.sold_date IS NULL" in _COMP_FEATURES_SQL


class TestHandlesNullGracefully:
    """Tests for NULL/missing data handling."""

    def test_handles_null_sqft_gracefully(self):
        """Properties with NULL sqft are excluded from subjects CTE."""
        from pricepoint.features.comparables import _COMP_FEATURES_SQL

        assert "sqft IS NOT NULL" in _COMP_FEATURES_SQL

    def test_null_price_features_when_no_comps(self):
        """When comp_count=0, price features should be NULL."""
        df = _make_raw_df(
            [1],
            comp_counts=[0],
            median_ppsfs=[None],
            adjusted_prices=[None],
            nearest_prices=[None],
            price_spreads=[None],
            avg_days=[None],
            nearest_dists=[None],
        )
        result = _compute_derived(df)

        assert result.loc[0, "comp_count"] == 0
        assert pd.isna(result.loc[0, "comp_median_ppsf"])
        assert pd.isna(result.loc[0, "comp_mean_adjusted_price"])
        assert pd.isna(result.loc[0, "comp_nearest_price"])
        assert pd.isna(result.loc[0, "comp_ppsf_ratio"])
