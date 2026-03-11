"""Unit tests for housing feature engineering."""

from __future__ import annotations

from datetime import UTC, datetime
from math import exp
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pricepoint.db.models import (
    RedfinListing,
    SaleHistoryRecord,
)
from pricepoint.features.housing import (
    AMENITY_COLUMNS,
    BOOLEAN_FEATURE_COLUMNS,
    CATEGORICAL_COLUMNS,
    DECAY_LAMBDA,
    NUMERIC_LISTING_COLUMNS,
    _compute_property_features,
    _compute_sale_features,
    _safe_div,
    build_housing_features,
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
        # All boolean columns default to False
        **{col: False for col in AMENITY_COLUMNS},
        **{col: False for col in BOOLEAN_FEATURE_COLUMNS},
        # Numeric listing columns default to None
        **{col: None for col in NUMERIC_LISTING_COLUMNS},
        # Categorical columns default to None
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
        "date": datetime(2024, 6, 1),
        "event": "Sold",
        "price": 340000.0,
        "source": "mls",
    }
    defaults.update(overrides)
    obj = MagicMock()
    for key, val in defaults.items():
        setattr(obj, key, val)
    return obj


class TestSafeDiv:
    def test_normal_division(self):
        assert _safe_div(10.0, 2.0) == 5.0

    def test_zero_denominator(self):
        assert _safe_div(10.0, 0) is None

    def test_none_numerator(self):
        assert _safe_div(None, 2.0) is None

    def test_none_denominator(self):
        assert _safe_div(10.0, None) is None


class TestComputePropertyFeatures:
    def test_basic_property_features(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(year_built=2000)
        result = _compute_property_features(listing, now)

        assert result["property_id"] == 1
        assert result["property_age"] == 26
        assert result["is_renovated"] is False
        assert result["years_since_renovation"] is None

    def test_renovated_property(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(year_renovated=2020)
        result = _compute_property_features(listing, now)

        assert result["is_renovated"] is True
        assert result["years_since_renovation"] == 6

    def test_bed_bath_ratio_zero_baths(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(num_baths=0)
        result = _compute_property_features(listing, now)
        assert result["bed_bath_ratio"] is None

    def test_sqft_per_bedroom_zero_beds(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(num_beds=0)
        result = _compute_property_features(listing, now)
        assert result["sqft_per_bedroom"] is None

    def test_lot_to_building_ratio(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(lot_size=8000.0, building_area=2000.0)
        result = _compute_property_features(listing, now)
        assert result["lot_to_building_ratio"] == 4.0

    def test_luxury_feature_count(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(
            has_private_pool=True,
            has_outdoor_kitchen=True,
            has_sauna=True,
        )
        result = _compute_property_features(listing, now)
        assert result["luxury_feature_count"] == 3

    def test_amenity_score(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(
            has_garage=True,
            has_fireplace=True,
            has_hardwood=True,
        )
        result = _compute_property_features(listing, now)
        assert result["amenity_score"] == 3

    def test_boolean_features_present(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(has_garage=True, has_fireplace=False)
        result = _compute_property_features(listing, now)
        for col in BOOLEAN_FEATURE_COLUMNS:
            assert col in result
        assert result["has_garage"] is True
        assert result["has_fireplace"] is False

    def test_numeric_listing_features_present(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(flood_score=3, fire_score=5, num_garage_spaces=2)
        result = _compute_property_features(listing, now)
        for col in NUMERIC_LISTING_COLUMNS:
            assert col in result
        assert result["flood_score"] == 3
        assert result["fire_score"] == 5
        assert result["num_garage_spaces"] == 2

    def test_categorical_features_present(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(parking_type="Attached", facade_type="Brick")
        result = _compute_property_features(listing, now)
        for col in CATEGORICAL_COLUMNS:
            assert col in result
        assert result["parking_type"] == "Attached"
        assert result["facade_type"] == "Brick"


class TestComputeSaleFeatures:
    def test_no_sales(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        result = _compute_sale_features([], now)
        assert result["years_since_last_sale"] is None
        assert result["decayed_sale_signal"] is None

    def test_single_sale(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        rec = _make_sale_record(event="SOLD", date=datetime(2024, 2, 19), price=300000.0)
        result = _compute_sale_features([rec], now)
        assert result["years_since_last_sale"] == pytest.approx(2.0, abs=0.02)
        expected_decay = 300000.0 * exp(-DECAY_LAMBDA * result["years_since_last_sale"])
        assert result["decayed_sale_signal"] == pytest.approx(expected_decay, rel=1e-4)

    def test_two_sales_uses_latest(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        old = _make_sale_record(event="SOLD", date=datetime(2020, 6, 1), price=250000.0)
        new = _make_sale_record(event="SOLD", date=datetime(2024, 6, 1), price=340000.0)
        result = _compute_sale_features([old, new], now)
        # Should use latest sale (340000) for decayed signal
        assert result["decayed_sale_signal"] is not None
        assert result["decayed_sale_signal"] < 340000.0

    def test_non_sold_events_excluded(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listed = _make_sale_record(event="Listed", date=datetime(2024, 1, 1), price=350000.0)
        sold = _make_sale_record(event="Sold", date=datetime(2024, 6, 1), price=340000.0)
        result = _compute_sale_features([listed, sold], now)
        # Only the Sold event should contribute
        assert result["years_since_last_sale"] is not None
        assert result["decayed_sale_signal"] is not None

    def test_decayed_sale_signal_none_price(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        rec = _make_sale_record(event="SOLD", date=datetime(2024, 2, 19), price=None)
        result = _compute_sale_features([rec], now)
        assert result["decayed_sale_signal"] is None


class TestBuildHousingFeatures:
    def test_empty_listings(self):
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        result = build_housing_features(db, property_ids=[999])
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_full_pipeline(self):
        """Integration-style test with mocked DB session."""
        listing = _make_listing(
            id=10,
            year_built=2005,
            listing_price=400000.0,
            sold_price=395000.0,
            sold_date=datetime(2025, 6, 1, tzinfo=UTC),
            contract_date=datetime(2025, 3, 1, tzinfo=UTC),
            num_beds=4,
            num_baths=3.0,
            sqft=2400,
            lot_size=10000.0,
            building_area=2400.0,
            zip_code="27601",
            city="Raleigh",
            price_per_sqft=166.67,
            has_private_pool=True,
            has_garage=True,
            parking_type="Attached",
            flood_score=2,
        )

        sale1 = _make_sale_record(
            property_id=10, event="SOLD", date=datetime(2020, 1, 1), price=300000.0
        )
        sale2 = _make_sale_record(
            property_id=10, event="SOLD", date=datetime(2025, 6, 1), price=395000.0
        )

        # Set up DB mock
        db = MagicMock()

        def query_side_effect(*args):
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q

            model = args[0] if args else None
            if model is RedfinListing:
                mock_q.all.return_value = [listing]
            elif model is SaleHistoryRecord:
                mock_q.all.return_value = [sale1, sale2]
            else:
                mock_q.all.return_value = []
            return mock_q

        db.query.side_effect = query_side_effect

        result = build_housing_features(db, property_ids=[10])

        assert isinstance(result, pd.DataFrame)
        assert 10 in result.index
        row = result.loc[10]

        # Property age
        current_year = datetime.now(tz=UTC).year
        assert row["property_age"] == current_year - 2005

        # Bed bath ratio
        assert row["bed_bath_ratio"] == pytest.approx(4 / 3, rel=1e-3)

        # Sale features
        assert row["years_since_last_sale"] is not None
        assert row["decayed_sale_signal"] is not None

        # Luxury + amenity
        assert row["luxury_feature_count"] == 1  # pool only
        assert row["amenity_score"] == 2  # pool + garage

        # Boolean features
        assert row["has_garage"] == True  # noqa: E712
        assert row["has_private_pool"] == True  # noqa: E712

        # Numeric listing features
        assert row["flood_score"] == 2

        # Categorical features
        assert row["parking_type"] == "Attached"

    def test_categorical_columns_have_category_dtype(self):
        """Categorical columns should be cast to category dtype."""
        listing = _make_listing(id=1, parking_type="Attached", facade_type="Brick")

        db = MagicMock()

        def query_side_effect(*args):
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q

            model = args[0] if args else None
            if model is RedfinListing:
                mock_q.all.return_value = [listing]
            elif model is SaleHistoryRecord:
                mock_q.all.return_value = []
            else:
                mock_q.all.return_value = []
            return mock_q

        db.query.side_effect = query_side_effect

        result = build_housing_features(db, property_ids=[1])

        for col in CATEGORICAL_COLUMNS:
            if col in result.columns:
                assert result[col].dtype.name == "category"
