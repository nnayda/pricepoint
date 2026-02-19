"""Unit tests for housing feature engineering."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pricepoint.db.models import (
    PropertyValuation,
    RedfinListing,
    SaleHistoryRecord,
    TaxHistoryRecord,
)
from pricepoint.features.housing import (
    AMENITY_COLUMNS,
    _compute_price_features,
    _compute_property_features,
    _compute_sale_features,
    _compute_tax_features,
    _compute_zip_and_city_aggregates,
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
    }
    defaults.update(overrides)
    listing = MagicMock()
    for key, val in defaults.items():
        setattr(listing, key, val)
    return listing


def _make_tax_record(**overrides):
    """Create a mock TaxHistoryRecord."""
    defaults = {
        "property_id": 1,
        "date": datetime(2024, 1, 1),
        "property_tax": 3500.0,
        "assessment_value_land": 80000.0,
        "assessment_value_additions": 220000.0,
        "assessment_value": 300000.0,
        "source": "county",
    }
    defaults.update(overrides)
    obj = MagicMock()
    for key, val in defaults.items():
        setattr(obj, key, val)
    return obj


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

    def test_days_on_market_sold(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(
            contract_date=datetime(2024, 3, 1, tzinfo=UTC),
            sold_date=datetime(2024, 6, 1, tzinfo=UTC),
        )
        result = _compute_property_features(listing, now)
        assert result["days_on_market"] == 92

    def test_days_on_market_no_contract(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(contract_date=None, sold_date=None)
        result = _compute_property_features(listing, now)
        assert result["days_on_market"] is None

    def test_bed_bath_ratio_zero_baths(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(num_baths=0)
        result = _compute_property_features(listing, now)
        assert result["bed_bath_ratio"] == 0.0

    def test_sqft_per_bedroom_zero_beds(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listing = _make_listing(num_beds=0)
        result = _compute_property_features(listing, now)
        assert result["sqft_per_bedroom"] == 0.0

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


class TestComputePriceFeatures:
    def test_listing_premium(self):
        listing = _make_listing(listing_price=350000.0)
        result = _compute_price_features(listing, 300000.0)
        assert result["listing_premium_pct"] == pytest.approx(16.6667, rel=1e-3)

    def test_listing_premium_no_assessment(self):
        listing = _make_listing(listing_price=350000.0)
        result = _compute_price_features(listing, None)
        assert result["listing_premium_pct"] is None

    def test_sale_premium(self):
        listing = _make_listing(sold_price=340000.0, listing_price=350000.0)
        result = _compute_price_features(listing, 300000.0)
        assert result["sale_premium_pct"] == pytest.approx(-2.857, rel=1e-2)

    def test_sale_premium_no_listing_price(self):
        listing = _make_listing(sold_price=340000.0, listing_price=None)
        result = _compute_price_features(listing, 300000.0)
        assert result["sale_premium_pct"] is None


class TestComputeTaxFeatures:
    def test_empty_records(self):
        result = _compute_tax_features([])
        assert result["tax_assessed_value"] is None
        assert result["land_to_improvements_ratio"] is None
        assert result["effective_tax_rate"] is None

    def test_latest_record_selected(self):
        old = _make_tax_record(date=datetime(2022, 1, 1), assessment_value=250000.0)
        new = _make_tax_record(date=datetime(2024, 1, 1), assessment_value=300000.0)
        result = _compute_tax_features([old, new])
        assert result["tax_assessed_value"] == 300000.0

    def test_land_to_improvements(self):
        rec = _make_tax_record(assessment_value_land=80000.0, assessment_value_additions=220000.0)
        result = _compute_tax_features([rec])
        assert result["land_to_improvements_ratio"] == pytest.approx(0.3636, rel=1e-2)

    def test_effective_tax_rate(self):
        rec = _make_tax_record(property_tax=3500.0, assessment_value=300000.0)
        result = _compute_tax_features([rec])
        assert result["effective_tax_rate"] == pytest.approx(0.01167, rel=1e-2)


class TestComputeSaleFeatures:
    def test_no_sales(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        result = _compute_sale_features([], now)
        assert result["num_prior_sales"] == 0
        assert result["years_since_last_sale"] is None
        assert result["price_yoy_change_pct"] is None

    def test_single_sale(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        rec = _make_sale_record(event="SOLD", date=datetime(2024, 2, 19), price=300000.0)
        result = _compute_sale_features([rec], now)
        assert result["num_prior_sales"] == 1
        assert result["years_since_last_sale"] == pytest.approx(2.0, abs=0.02)
        assert result["price_yoy_change_pct"] is None

    def test_two_sales_yoy(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        old = _make_sale_record(event="SOLD", date=datetime(2020, 6, 1), price=250000.0)
        new = _make_sale_record(event="SOLD", date=datetime(2024, 6, 1), price=340000.0)
        result = _compute_sale_features([old, new], now)
        assert result["num_prior_sales"] == 2
        assert result["price_yoy_change_pct"] == pytest.approx(36.0, rel=1e-2)

    def test_non_sold_events_excluded(self):
        now = datetime(2026, 2, 19, tzinfo=UTC)
        listed = _make_sale_record(event="Listed", date=datetime(2024, 1, 1), price=350000.0)
        sold = _make_sale_record(event="Sold", date=datetime(2024, 6, 1), price=340000.0)
        result = _compute_sale_features([listed, sold], now)
        assert result["num_prior_sales"] == 1


class TestComputeZipAndCityAggregates:
    def test_empty_results(self):
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        result = _compute_zip_and_city_aggregates(db, None)
        assert result.empty

    def test_aggregates_computed(self):
        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query

        # Return tuples matching (id, zip_code, city, sold_price, price_per_sqft)
        mock_query.all.return_value = [
            (1, "27601", "Raleigh", 300000.0, 150.0),
            (2, "27601", "Raleigh", 400000.0, 200.0),
            (3, "27513", "Cary", 500000.0, 250.0),
        ]

        result = _compute_zip_and_city_aggregates(db, [1, 2, 3])
        assert len(result) == 3
        # Zip 27601 median = 350000
        assert result.loc[1, "zip_median_price"] == 350000.0
        assert result.loc[2, "zip_median_price"] == 350000.0
        # Cary single entry median = 500000
        assert result.loc[3, "city_median_price"] == 500000.0


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
        )

        tax = _make_tax_record(
            property_id=10,
            date=datetime(2024, 1, 1),
            assessment_value=350000.0,
            assessment_value_land=100000.0,
            assessment_value_additions=250000.0,
            property_tax=4200.0,
        )

        sale1 = _make_sale_record(
            property_id=10, event="SOLD", date=datetime(2020, 1, 1), price=300000.0
        )
        sale2 = _make_sale_record(
            property_id=10, event="SOLD", date=datetime(2025, 6, 1), price=395000.0
        )

        valuation = MagicMock()
        valuation.property_id = 10
        valuation.value = 390000.0
        valuation.source = "redfin"

        # Set up DB mock
        db = MagicMock()

        def query_side_effect(*args):
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q

            model = args[0] if args else None
            if model is RedfinListing:
                mock_q.all.return_value = [listing]
            elif model is TaxHistoryRecord:
                mock_q.all.return_value = [tax]
            elif model is SaleHistoryRecord:
                mock_q.all.return_value = [sale1, sale2]
            elif model is PropertyValuation:
                mock_q.all.return_value = [valuation]
            else:
                # Multi-column queries (zip/city aggregates) return empty
                mock_q.filter.return_value = mock_q
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

        # Tax features
        assert row["tax_assessed_value"] == 350000.0
        assert row["effective_tax_rate"] == pytest.approx(0.012, rel=1e-2)

        # Sale features
        assert row["num_prior_sales"] == 2
        assert row["price_yoy_change_pct"] == pytest.approx(31.667, rel=1e-2)

        # Listing premium
        assert row["listing_premium_pct"] == pytest.approx(14.286, rel=1e-2)

        # Redfin estimate diff
        assert row["redfin_estimate_diff_pct"] == pytest.approx(2.564, rel=1e-2)

        # Luxury + amenity
        assert row["luxury_feature_count"] == 1  # pool only
        assert row["amenity_score"] == 2  # pool + garage
