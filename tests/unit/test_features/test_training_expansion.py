"""Unit tests for multi-sale training record expansion.

Tests the new functions that expand the training dataset to include
one row per historical SOLD event per property.
"""

from __future__ import annotations

from datetime import UTC, datetime
from math import exp
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from pricepoint.db.models import RedfinListing
from pricepoint.features.housing import (
    AMENITY_COLUMNS,
    BOOLEAN_FEATURE_COLUMNS,
    CATEGORICAL_COLUMNS,
    DECAY_LAMBDA,
    NUMERIC_LISTING_COLUMNS,
    _compute_property_features_as_of,
    build_training_sale_events,
)


def _make_listing(**overrides):
    """Create a mock RedfinListing with sensible defaults."""
    defaults = {
        "id": 1,
        "year_built": 2000,
        "year_renovated": None,
        "sold_date": datetime(2024, 6, 1, tzinfo=UTC),
        "contract_date": datetime(2024, 3, 1, tzinfo=UTC),
        "num_beds": 3,
        "num_baths": 2.0,
        "sqft": 1800,
        "lot_size": 8000.0,
        "building_area": 2000.0,
        "listing_price": 350000.0,
        "sold_price": 340000.0,
        "zip_code": "27601",
        "city": "Raleigh",
        "price_per_sqft": 194.44,
        **{col: False for col in AMENITY_COLUMNS},
        **{col: False for col in BOOLEAN_FEATURE_COLUMNS},
        **{col: None for col in NUMERIC_LISTING_COLUMNS},
        **{col: None for col in CATEGORICAL_COLUMNS},
    }
    defaults.update(overrides)
    listing = MagicMock()
    for key, val in defaults.items():
        setattr(listing, key, val)
    return listing


def _make_sale_record(**overrides):
    """Create a mock SaleHistoryRecord."""
    defaults = {
        "property_id": 1,
        "date": datetime(2024, 6, 1, tzinfo=UTC),
        "event": "Sold",
        "price": 340000.0,
        "source": "mls",
    }
    defaults.update(overrides)
    obj = MagicMock()
    for key, val in defaults.items():
        setattr(obj, key, val)
    return obj


class TestComputePropertyFeaturesAsOf:
    """Tests for _compute_property_features_as_of."""

    def test_property_age_as_of_sale_date(self):
        listing = _make_listing(year_built=2000)
        now = datetime(2026, 3, 19, tzinfo=UTC)
        sale_date = datetime(2015, 6, 1, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=250000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        # property_age should be 2015 - 2000 = 15, NOT 2026 - 2000 = 26
        assert result["property_age"] == 15

    def test_renovation_before_sale_is_included(self):
        listing = _make_listing(year_built=1990, year_renovated=2010)
        now = datetime(2026, 3, 19, tzinfo=UTC)
        sale_date = datetime(2015, 6, 1, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=300000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        assert result["is_renovated"] is True
        assert result["years_since_renovation"] == 5  # 2015 - 2010

    def test_renovation_after_sale_is_excluded(self):
        listing = _make_listing(year_built=1990, year_renovated=2018)
        now = datetime(2026, 3, 19, tzinfo=UTC)
        sale_date = datetime(2015, 6, 1, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=200000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        assert result["is_renovated"] is False
        assert result["years_since_renovation"] is None

    def test_sale_chain_features(self):
        listing = _make_listing()
        now = datetime(2026, 3, 19, tzinfo=UTC)
        prior_date = datetime(2010, 1, 15, tzinfo=UTC)
        sale_date = datetime(2015, 6, 1, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=300000.0,
            prior_sale_date=prior_date,
            prior_sale_price=200000.0,
            is_most_recent=False,
            now=now,
        )

        expected_years = (sale_date - prior_date).days / 365.25
        assert result["years_since_last_sale"] == pytest.approx(expected_years, abs=0.01)
        expected_decay = 200000.0 * exp(-DECAY_LAMBDA * expected_years)
        assert result["decayed_sale_signal"] == pytest.approx(expected_decay, rel=1e-6)

    def test_no_prior_sale(self):
        listing = _make_listing()
        now = datetime(2026, 3, 19, tzinfo=UTC)
        sale_date = datetime(2015, 6, 1, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=250000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=True,
            now=now,
        )

        assert result["years_since_last_sale"] is None
        assert result["decayed_sale_signal"] is None

    def test_is_historical_flag(self):
        listing = _make_listing()
        now = datetime(2026, 3, 19, tzinfo=UTC)

        result_historical = _compute_property_features_as_of(
            listing=listing,
            sale_date=datetime(2015, 6, 1, tzinfo=UTC),
            sale_price=250000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        result_recent = _compute_property_features_as_of(
            listing=listing,
            sale_date=datetime(2024, 6, 1, tzinfo=UTC),
            sale_price=400000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=True,
            now=now,
        )

        assert result_historical["is_historical"] is True
        assert result_recent["is_historical"] is False

    def test_record_age_years(self):
        listing = _make_listing()
        now = datetime(2026, 3, 19, tzinfo=UTC)
        sale_date = datetime(2016, 3, 19, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=250000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        # Exactly 10 years (modulo leap years)
        assert result["record_age_years"] == pytest.approx(10.0, abs=0.02)

    def test_sale_event_id_format(self):
        listing = _make_listing(id=42)
        now = datetime(2026, 3, 19, tzinfo=UTC)
        sale_date = datetime(2020, 7, 15, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=sale_date,
            sale_price=300000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=True,
            now=now,
        )

        assert result["sale_event_id"] == "42_2020-07-15"

    def test_sold_price_is_sale_price(self):
        listing = _make_listing(sold_price=500000.0)
        now = datetime(2026, 3, 19, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=datetime(2020, 1, 1, tzinfo=UTC),
            sale_price=250000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        # Target is the historical sale price, NOT the listing's current sold_price
        assert result["sold_price"] == 250000.0

    def test_static_features_pass_through(self):
        listing = _make_listing(
            num_beds=4,
            num_baths=3.0,
            sqft=2400,
            has_private_pool=True,
            has_garage=True,
        )
        now = datetime(2026, 3, 19, tzinfo=UTC)

        result = _compute_property_features_as_of(
            listing=listing,
            sale_date=datetime(2020, 1, 1, tzinfo=UTC),
            sale_price=300000.0,
            prior_sale_date=None,
            prior_sale_price=None,
            is_most_recent=False,
            now=now,
        )

        assert result["bed_bath_ratio"] == pytest.approx(4 / 3)
        assert result["sqft_per_bedroom"] == pytest.approx(2400 / 4)
        assert result["has_private_pool"] is True
        assert result["has_garage"] is True


class TestBuildTrainingSaleEvents:
    """Tests for build_training_sale_events."""

    def _mock_db(self, listings, sale_records):
        """Create a mock DB session that returns given listings and sale records."""
        db = MagicMock()
        listing_query = MagicMock()
        listing_query.filter.return_value = listing_query
        listing_query.all.return_value = listings
        sale_query = MagicMock()
        sale_query.filter.return_value = sale_query
        sale_query.all.return_value = sale_records
        db.query.side_effect = lambda model: listing_query if model is RedfinListing else sale_query
        return db

    def test_property_with_three_sold_events(self):
        listing = _make_listing(id=1, year_built=1990)
        d = UTC
        sales = [
            _make_sale_record(property_id=1, date=datetime(2005, 3, 1, tzinfo=d), price=150000.0),
            _make_sale_record(property_id=1, date=datetime(2012, 8, 15, tzinfo=d), price=220000.0),
            _make_sale_record(property_id=1, date=datetime(2020, 11, 1, tzinfo=d), price=350000.0),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)

        assert len(df) == 3
        assert df["property_id"].nunique() == 1
        # Verify chronological order and is_historical flags
        assert df.iloc[0]["is_historical"] == True  # noqa: E712
        assert df.iloc[1]["is_historical"] == True  # noqa: E712
        assert df.iloc[2]["is_historical"] == False  # noqa: E712
        # Verify targets
        assert df.iloc[0]["sold_price"] == 150000.0
        assert df.iloc[1]["sold_price"] == 220000.0
        assert df.iloc[2]["sold_price"] == 350000.0

    def test_property_with_single_sold_event(self):
        listing = _make_listing(id=1)
        sales = [
            _make_sale_record(property_id=1, date=datetime(2024, 6, 1, tzinfo=UTC), price=340000.0),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)

        assert len(df) == 1
        assert df.iloc[0]["is_historical"] == False  # noqa: E712
        assert df.iloc[0]["sold_price"] == 340000.0

    def test_non_sold_events_excluded(self):
        listing = _make_listing(id=1)
        d = UTC
        sales = [
            _make_sale_record(
                property_id=1, date=datetime(2023, 1, 1, tzinfo=d), event="Listed", price=350000.0
            ),
            _make_sale_record(
                property_id=1, date=datetime(2023, 2, 1, tzinfo=d), event="Pending", price=340000.0
            ),
            _make_sale_record(
                property_id=1, date=datetime(2023, 3, 1, tzinfo=d), event="Sold", price=340000.0
            ),
            _make_sale_record(
                property_id=1, date=datetime(2023, 4, 1, tzinfo=d), event="Price Change", price=None
            ),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)

        assert len(df) == 1
        assert df.iloc[0]["sold_price"] == 340000.0

    def test_min_sale_price_filters_nominal_transfers(self):
        listing = _make_listing(id=1)
        sales = [
            _make_sale_record(property_id=1, date=datetime(2015, 1, 1, tzinfo=UTC), price=100.0),
            _make_sale_record(property_id=1, date=datetime(2020, 6, 1, tzinfo=UTC), price=300000.0),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db, min_sale_price=10_000)

        assert len(df) == 1
        assert df.iloc[0]["sold_price"] == 300000.0

    def test_sale_chain_references_prior_sale(self):
        listing = _make_listing(id=1)
        sales = [
            _make_sale_record(property_id=1, date=datetime(2010, 1, 1, tzinfo=UTC), price=200000.0),
            _make_sale_record(property_id=1, date=datetime(2020, 1, 1, tzinfo=UTC), price=350000.0),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)

        # First sale has no prior
        assert pd.isna(df.iloc[0]["years_since_last_sale"])
        assert pd.isna(df.iloc[0]["decayed_sale_signal"])

        # Second sale references the first
        assert df.iloc[1]["years_since_last_sale"] is not None
        assert df.iloc[1]["years_since_last_sale"] == pytest.approx(10.0, abs=0.05)
        expected_decay = 200000.0 * exp(-DECAY_LAMBDA * df.iloc[1]["years_since_last_sale"])
        assert df.iloc[1]["decayed_sale_signal"] == pytest.approx(expected_decay, rel=1e-6)

    def test_renovation_between_sales(self):
        listing = _make_listing(id=1, year_built=1990, year_renovated=2015)
        sales = [
            _make_sale_record(property_id=1, date=datetime(2010, 6, 1, tzinfo=UTC), price=200000.0),
            _make_sale_record(property_id=1, date=datetime(2020, 6, 1, tzinfo=UTC), price=400000.0),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)

        # Pre-renovation sale (2010): renovation was 2015, so is_renovated=False
        assert df.iloc[0]["is_renovated"] == False  # noqa: E712
        assert pd.isna(df.iloc[0]["years_since_renovation"])

        # Post-renovation sale (2020): renovation was 2015, so is_renovated=True
        assert df.iloc[1]["is_renovated"] == True  # noqa: E712
        assert df.iloc[1]["years_since_renovation"] == 5  # 2020 - 2015

    def test_index_is_sale_event_id(self):
        listing = _make_listing(id=42)
        sales = [
            _make_sale_record(
                property_id=42, date=datetime(2020, 7, 15, tzinfo=UTC), price=300000.0
            ),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)

        assert df.index.name == "sale_event_id"
        assert "42_2020-07-15" in df.index

    def test_empty_listings_returns_empty(self):
        db = self._mock_db([], [])
        df = build_training_sale_events(db)
        assert df.empty

    def test_no_sold_events_returns_empty(self):
        listing = _make_listing(id=1)
        sales = [
            _make_sale_record(
                property_id=1, event="Listed", date=datetime(2023, 1, 1, tzinfo=UTC), price=350000.0
            ),
        ]

        db = self._mock_db([listing], sales)
        df = build_training_sale_events(db)
        assert df.empty

    def test_multiple_properties(self):
        listing1 = _make_listing(id=1)
        listing2 = _make_listing(id=2)
        sales = [
            _make_sale_record(property_id=1, date=datetime(2015, 1, 1, tzinfo=UTC), price=200000.0),
            _make_sale_record(property_id=1, date=datetime(2020, 1, 1, tzinfo=UTC), price=300000.0),
            _make_sale_record(property_id=2, date=datetime(2018, 6, 1, tzinfo=UTC), price=250000.0),
        ]

        db = self._mock_db([listing1, listing2], sales)
        df = build_training_sale_events(db)

        assert len(df) == 3
        assert df["property_id"].nunique() == 2


class TestTrainingEconomicFeatures:
    """Tests for build_training_economic_features."""

    def test_looks_up_by_sale_date(self):
        from pricepoint.features.economic import (
            SERIES_IDS,
            build_training_economic_features,
        )

        sale_events = pd.DataFrame(
            {
                "sale_event_id": ["1_2015-06-01", "1_2020-06-01"],
                "property_id": [1, 1],
                "sale_date": [
                    datetime(2015, 6, 1, tzinfo=UTC),
                    datetime(2020, 6, 1, tzinfo=UTC),
                ],
            }
        )

        db = MagicMock()
        # Build a cache with different values for 2015 vs 2020
        from datetime import date

        cache: dict[str, tuple[list[date], list[float]]] = {}
        for series_id in SERIES_IDS.values():
            cache[series_id] = (
                [date(2014, 1, 1), date(2015, 1, 1), date(2020, 1, 1)],
                [2.0, 3.5, 4.5],
            )

        with patch("pricepoint.features.economic._prefetch_series", return_value=cache):
            df = build_training_economic_features(db, sale_events)

        assert len(df) == 2
        assert df.index.name == "sale_event_id"
        # 2015-06-01 should get the 2015 value (3.5), 2020-06-01 should get 2020 value (4.5)
        assert df.loc["1_2015-06-01", "mortgage_rate_30yr"] == pytest.approx(3.5)
        assert df.loc["1_2020-06-01", "mortgage_rate_30yr"] == pytest.approx(4.5)

    def test_empty_input_returns_empty(self):
        from pricepoint.features.economic import build_training_economic_features

        empty = pd.DataFrame(columns=["sale_event_id", "property_id", "sale_date"])
        db = MagicMock()
        df = build_training_economic_features(db, empty)
        assert df.empty
        assert df.index.name == "sale_event_id"


class TestGroupedSplitting:
    """Tests for GroupShuffleSplit in train_model."""

    def test_no_property_id_leakage(self):
        """Verify that no property_id appears in both train and test sets."""
        from pricepoint.models.training import prepare_features

        rng = np.random.RandomState(42)
        n_properties = 50
        n_sales = 150  # ~3 sales per property

        property_ids = rng.randint(1, n_properties + 1, n_sales)
        sqft = rng.uniform(800, 4000, n_sales)
        sold_price = 50000 + 150 * sqft + rng.normal(0, 10000, n_sales)

        df = pd.DataFrame(
            {
                "property_id": property_ids,
                "sqft": sqft,
                "sold_price": sold_price,
                "is_historical": rng.choice([True, False], n_sales),
                "record_age_years": rng.uniform(0, 20, n_sales),
                "parking_type": pd.Categorical(rng.choice(["A", "B"], n_sales)),
            }
        )

        from sklearn.model_selection import GroupShuffleSplit

        groups = df["property_id"]
        x, y = prepare_features(df, "sold_price", filter_outliers=False)
        groups = groups.reindex(x.index)

        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(gss.split(x, y, groups=groups))

        train_props = set(groups.iloc[train_idx].unique())
        test_props = set(groups.iloc[test_idx].unique())

        # No overlap!
        assert train_props.isdisjoint(test_props)

    def test_metadata_columns_dropped(self):
        """Verify that property_id, sale_event_id, sale_date are dropped."""
        from pricepoint.models.training import prepare_features

        rng = np.random.RandomState(42)
        n = 100

        df = pd.DataFrame(
            {
                "property_id": rng.randint(1, 20, n),
                "sale_event_id": [f"{i}_2020-01-01" for i in range(n)],
                "sale_date": pd.date_range("2020-01-01", periods=n, freq="D"),
                "sqft": rng.uniform(800, 4000, n),
                "is_historical": rng.choice([True, False], n),
                "record_age_years": rng.uniform(0, 20, n),
                "sold_price": rng.uniform(100000, 500000, n),
            }
        )

        x, y = prepare_features(df, "sold_price", filter_outliers=False)

        assert "property_id" not in x.columns
        assert "sale_event_id" not in x.columns
        assert "sale_date" not in x.columns
        # These are kept as features
        assert "is_historical" in x.columns
        assert "record_age_years" in x.columns


class TestGroupedCrossValidation:
    """Tests for GroupKFold in cross_validate."""

    def test_grouped_cv_no_leakage(self):
        """Verify that GroupKFold keeps properties together in folds."""
        from sklearn.model_selection import GroupKFold

        rng = np.random.RandomState(42)
        n_properties = 30
        n_sales = 90

        property_ids = rng.randint(1, n_properties + 1, n_sales)
        sqft = rng.uniform(800, 4000, n_sales)
        sold_price = 50000 + 150 * sqft + rng.normal(0, 10000, n_sales)

        df = pd.DataFrame(
            {
                "property_id": property_ids,
                "sqft": sqft,
                "sold_price": sold_price,
                "is_historical": rng.choice([True, False], n_sales),
                "record_age_years": rng.uniform(0, 20, n_sales),
                "parking_type": pd.Categorical(rng.choice(["A", "B"], n_sales)),
            }
        )

        from pricepoint.models.training import prepare_features

        groups = df["property_id"]
        x, y = prepare_features(df, "sold_price", filter_outliers=False)
        groups = groups.reindex(x.index)

        gkf = GroupKFold(n_splits=5)
        for train_idx, test_idx in gkf.split(x, y, groups=groups):
            train_props = set(groups.iloc[train_idx].unique())
            test_props = set(groups.iloc[test_idx].unique())
            assert train_props.isdisjoint(test_props)
