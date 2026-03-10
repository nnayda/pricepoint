"""Tests for the comparables nearest-neighbour module."""

import numpy as np
import pandas as pd
import pytest

from pricepoint.api.services.comparables_nn import find_nearest_comparables


def _make_df(n: int = 10, *, include_sold_price: bool = True) -> pd.DataFrame:
    """Build a synthetic feature matrix for testing."""
    rng = np.random.default_rng(42)
    data = {
        "sqft": rng.integers(1000, 4000, size=n).astype(float),
        "num_beds": rng.integers(2, 6, size=n).astype(float),
        "num_baths": rng.integers(1, 4, size=n).astype(float),
        "property_age": rng.integers(1, 50, size=n).astype(float),
        "amenity_score": rng.integers(0, 20, size=n).astype(float),
        "has_garage": rng.choice([True, False], size=n),
        "has_pool": rng.choice([True, False], size=n),
    }
    if include_sold_price:
        data["sold_price"] = rng.integers(200_000, 800_000, size=n).astype(float)
    df = pd.DataFrame(data)
    df.index = pd.Index(range(100, 100 + n), name="property_id")
    return df


class TestFindNearestComparables:
    """Tests for find_nearest_comparables."""

    def test_returns_top_n(self):
        df = _make_df(10)
        result = find_nearest_comparables(df, subject_id=100, n=5)
        assert len(result) == 5

    def test_excludes_subject(self):
        df = _make_df(10)
        result = find_nearest_comparables(df, subject_id=100, n=9)
        ids = [pid for pid, _ in result]
        assert 100 not in ids

    def test_sorted_ascending(self):
        df = _make_df(10)
        result = find_nearest_comparables(df, subject_id=100, n=5)
        distances = [d for _, d in result]
        assert distances == sorted(distances)

    def test_distances_are_non_negative(self):
        df = _make_df(10)
        result = find_nearest_comparables(df, subject_id=100, n=5)
        for _, dist in result:
            assert dist >= 0

    def test_subject_not_in_df_returns_empty(self):
        df = _make_df(5)
        result = find_nearest_comparables(df, subject_id=999, n=3)
        assert result == []

    def test_fewer_than_n_candidates(self):
        df = _make_df(3)
        result = find_nearest_comparables(df, subject_id=100, n=5)
        assert len(result) == 2  # 3 total minus subject

    def test_handles_nan_values(self):
        df = _make_df(6)
        df.loc[101, "sqft"] = np.nan
        df.loc[102, "num_beds"] = np.nan
        df.loc[103, "property_age"] = np.nan
        result = find_nearest_comparables(df, subject_id=100, n=5)
        assert len(result) == 5
        for _, dist in result:
            assert np.isfinite(dist)

    def test_handles_categorical_columns(self):
        df = _make_df(6)
        df["parking_type"] = pd.Categorical(
            ["attached", "detached", "attached", "none", "detached", "attached"]
        )
        result = find_nearest_comparables(df, subject_id=100, n=3)
        assert len(result) == 3

    def test_drops_sold_price(self):
        """sold_price should not influence similarity."""
        df = _make_df(6, include_sold_price=True)
        # Make two properties identical except for sold_price
        for col in df.columns:
            if col != "sold_price":
                df.loc[101, col] = df.loc[100, col]
        df.loc[101, "sold_price"] = df.loc[100, "sold_price"] + 500_000

        result = find_nearest_comparables(df, subject_id=100, n=1)
        # Closest should be 101 (identical features, different sold_price)
        assert result[0][0] == 101
        assert result[0][1] == pytest.approx(0.0, abs=1e-6)

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = find_nearest_comparables(df, subject_id=100, n=5)
        assert result == []

    def test_single_property(self):
        df = _make_df(1)
        result = find_nearest_comparables(df, subject_id=100, n=5)
        assert result == []  # No candidates besides subject
