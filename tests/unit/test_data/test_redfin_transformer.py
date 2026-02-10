"""Tests for the Redfin staging-to-production transformer."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.housing.redfin_transformer import (
    compute_staging_hash,
    extract_exterior,
    extract_financial,
    extract_interior,
    map_climate_score,
    parse_lot_size_sqft,
    parse_price,
    parse_sale_history,
    parse_school_desc,
    parse_tax_history,
    transform_all_listings,
    transform_listing,
)


# ---------------------------------------------------------------------------
# TestParsePrice
# ---------------------------------------------------------------------------
class TestParsePrice:
    def test_valid_price(self):
        assert parse_price("$721,000") == 721000.0

    def test_none_input(self):
        assert parse_price(None) is None

    def test_empty_string(self):
        assert parse_price("") is None

    def test_no_dollar_sign(self):
        assert parse_price("500000") == 500000.0

    def test_with_cents(self):
        assert parse_price("$1,234.56") == 1234.56

    def test_non_numeric(self):
        assert parse_price("N/A") is None


# ---------------------------------------------------------------------------
# TestParseLotSize
# ---------------------------------------------------------------------------
class TestParseLotSize:
    def test_acres(self):
        result = parse_lot_size_sqft("0.25 Acres")
        assert result == pytest.approx(10890.0)

    def test_sqft(self):
        assert parse_lot_size_sqft("8,500 Sq. Ft.") == 8500.0

    def test_none_input(self):
        assert parse_lot_size_sqft(None) is None

    def test_unparseable(self):
        assert parse_lot_size_sqft("unknown") is None

    def test_case_insensitive_acres(self):
        result = parse_lot_size_sqft("1.0 ACRES")
        assert result == pytest.approx(43560.0)

    def test_case_insensitive_sqft(self):
        assert parse_lot_size_sqft("5000 sq ft") == 5000.0


# ---------------------------------------------------------------------------
# TestClimateRiskScore
# ---------------------------------------------------------------------------
class TestClimateRiskScore:
    def test_extreme(self):
        assert map_climate_score("Extreme") == 10

    def test_severe(self):
        assert map_climate_score("Severe") == 8

    def test_major(self):
        assert map_climate_score("Major") == 7

    def test_moderate(self):
        assert map_climate_score("Moderate") == 5

    def test_minor(self):
        assert map_climate_score("Minor") == 3

    def test_minimal(self):
        assert map_climate_score("Minimal") == 1

    def test_unknown(self):
        assert map_climate_score("Unknown") is None

    def test_none(self):
        assert map_climate_score(None) is None

    def test_case_insensitive(self):
        assert map_climate_score("MAJOR") == 7


# ---------------------------------------------------------------------------
# TestExtractInterior
# ---------------------------------------------------------------------------
class TestExtractInterior:
    def test_full_extraction(self):
        details = {
            "Interior": ["Flooring: Hardwood, Tile", "Appliances: Dishwasher, Microwave"],
            "Heating & Cooling": ["Heating: Forced Air", "Cooling: Central Air"],
        }
        result = extract_interior(details)
        assert result["flooring"] == ["Hardwood", "Tile"]
        assert result["appliances"] == ["Dishwasher", "Microwave"]
        assert result["heating"] == "Forced Air"
        assert result["cooling"] == "Central Air"

    def test_empty_input(self):
        result = extract_interior(None)
        assert result["flooring"] == []
        assert result["appliances"] == []
        assert result["heating"] is None
        assert result["cooling"] is None

    def test_multi_value_flooring(self):
        details = {"Interior": ["Flooring: Hardwood, Carpet, Tile"]}
        result = extract_interior(details)
        assert result["flooring"] == ["Hardwood", "Carpet", "Tile"]

    def test_missing_group(self):
        details = {"Interior": ["Flooring: Hardwood"]}
        result = extract_interior(details)
        assert result["heating"] is None
        assert result["cooling"] is None

    def test_fireplace(self):
        details = {"Interior": ["Fireplace: Gas Log"]}
        result = extract_interior(details)
        assert result["fireplace"] == "Gas Log"

    def test_basement(self):
        details = {"Interior": ["Basement: Finished"]}
        result = extract_interior(details)
        assert result["basement"] == "Finished"


# ---------------------------------------------------------------------------
# TestExtractExterior
# ---------------------------------------------------------------------------
class TestExtractExterior:
    def test_full_extraction(self):
        details = {
            "Exterior": ["Roof: Asphalt Shingle", "Fencing: Wood", "Pool: In-Ground"],
            "Parking": ["Garage Spaces: 2", "Attached Garage: Yes"],
        }
        result = extract_exterior(details)
        assert result["roof"] == "Asphalt Shingle"
        assert result["fence"] == "Wood"
        assert result["pool"] == "In-Ground"
        assert result["garage_spaces"] == 2

    def test_garage_spaces_parsing(self):
        details = {"Parking": ["Garage Spaces: 3"]}
        result = extract_exterior(details)
        assert result["garage_spaces"] == 3

    def test_fence_is_string(self):
        details = {"Exterior": ["Fencing: Chain Link"]}
        result = extract_exterior(details)
        assert result["fence"] == "Chain Link"
        assert isinstance(result["fence"], str)

    def test_empty_input(self):
        result = extract_exterior(None)
        assert result["roof"] is None
        assert result["garage_spaces"] is None

    def test_pool_string(self):
        details = {"Exterior": ["Pool Features: Heated"]}
        result = extract_exterior(details)
        assert result["pool"] == "Heated"


# ---------------------------------------------------------------------------
# TestExtractFinancial
# ---------------------------------------------------------------------------
class TestExtractFinancial:
    def test_from_tax_history(self):
        tax = [{"year": 2024, "tax": "$4,000", "assessed_value": "$400,000"}]
        result = extract_financial(None, tax)
        assert result["tax_annual"] == 4000.0
        assert result["tax_year"] == 2024
        assert result["assessed_value"] == 400000.0

    def test_hoa_from_property_details(self):
        details = {"Financial": ["HOA Dues: $150"]}
        result = extract_financial(details, None)
        assert result["hoa_monthly"] == 150.0

    def test_empty(self):
        result = extract_financial(None, None)
        assert result["hoa_monthly"] is None
        assert result["tax_annual"] is None
        assert result["tax_year"] is None
        assert result["assessed_value"] is None


# ---------------------------------------------------------------------------
# TestParseSchoolDesc
# ---------------------------------------------------------------------------
class TestParseSchoolDesc:
    def test_public_elementary(self):
        result = parse_school_desc("Public, PreK-5 Assigned 0.3mi")
        assert result["school_type"] == "Public"
        assert result["grades"] == "PreK-5"
        assert result["distance_miles"] == pytest.approx(0.3)

    def test_private_school(self):
        result = parse_school_desc("Private, 9-12 Nearby 2.1mi")
        assert result["school_type"] == "Private"
        assert result["grades"] == "9-12"
        assert result["distance_miles"] == pytest.approx(2.1)

    def test_no_distance(self):
        result = parse_school_desc("Public, K-8 Assigned")
        assert result["school_type"] == "Public"
        assert result["grades"] == "K-8"
        assert result["distance_miles"] is None

    def test_none_input(self):
        assert parse_school_desc(None) is None


# ---------------------------------------------------------------------------
# TestParseSaleHistory
# ---------------------------------------------------------------------------
class TestParseSaleHistory:
    def test_valid_entries(self):
        raw = [
            {"date": "2020-01-15", "event": "Sold", "price": "$300,000"},
            {"date": "2022-06-01", "event": "Listed", "price": "$350,000"},
        ]
        result = parse_sale_history(raw)
        assert len(result) == 2
        assert result[0]["price"] == 300000.0
        assert result[0]["event_type"] == "Sold"

    def test_none_input(self):
        assert parse_sale_history(None) == []

    def test_empty_list(self):
        assert parse_sale_history([]) == []

    def test_price_parsing(self):
        raw = [{"date": "2020-01-01", "event": "Sold", "price": "$1,234,567"}]
        result = parse_sale_history(raw)
        assert result[0]["price"] == 1234567.0


# ---------------------------------------------------------------------------
# TestParseTaxHistory
# ---------------------------------------------------------------------------
class TestParseTaxHistory:
    def test_valid(self):
        raw = [
            {"year": 2023, "tax": "$3,500", "assessed_value": "$350,000"},
            {"year": 2024, "tax": "$4,000", "assessed_value": "$400,000"},
        ]
        result = parse_tax_history(raw)
        assert len(result) == 2
        # Sorted descending by year
        assert result[0]["year"] == 2024
        assert result[0]["tax_amount"] == 4000.0

    def test_none_input(self):
        assert parse_tax_history(None) == []

    def test_dollar_stripping(self):
        raw = [{"year": 2024, "tax": "$1,234", "assessed_value": "$100,000"}]
        result = parse_tax_history(raw)
        assert result[0]["tax_amount"] == 1234.0
        assert result[0]["assessed_value"] == 100000.0

    def test_string_year(self):
        raw = [{"year": "2023", "tax": "$3,000", "assessed_value": "$300,000"}]
        result = parse_tax_history(raw)
        assert result[0]["year"] == 2023


# ---------------------------------------------------------------------------
# TestComputeHash
# ---------------------------------------------------------------------------
class TestComputeHash:
    def _make_staging(self, **kwargs):
        """Create a mock StagingRedfinListing."""
        mock = MagicMock()
        mock.address = kwargs.get("address", "123 Main St")
        mock.city = kwargs.get("city", "Cary")
        mock.state = kwargs.get("state", "NC")
        mock.zip_code = kwargs.get("zip_code", "27513")
        mock.listing_status = kwargs.get("listing_status", "Sold")
        mock.sold_date = kwargs.get("sold_date", "Jan 1, 2024")
        mock.sold_price = kwargs.get("sold_price", "$500,000")
        mock.listing_price = kwargs.get("listing_price", "$510,000")
        mock.beds = kwargs.get("beds", 3)
        mock.baths = kwargs.get("baths", 2.5)
        mock.sqft = kwargs.get("sqft", 2000)
        mock.description = kwargs.get("description", "Nice home")
        mock.year_built = kwargs.get("year_built", 2005)
        mock.lot_size = kwargs.get("lot_size", "0.25 Acres")
        mock.price_per_sqft = kwargs.get("price_per_sqft", "$250")
        mock.listing_agent = kwargs.get("listing_agent", "Agent A")
        mock.listing_brokerage = kwargs.get("listing_brokerage", "Broker A")
        mock.buying_agent = kwargs.get("buying_agent", "Agent B")
        mock.buying_brokerage = kwargs.get("buying_brokerage", "Broker B")
        mock.redfin_estimate = kwargs.get("redfin_estimate", "$490,000")
        mock.sale_history = kwargs.get("sale_history", [])
        mock.tax_history = kwargs.get("tax_history", [])
        mock.property_details = kwargs.get("property_details", {})
        mock.schools = kwargs.get("schools", [])
        mock.climate_flood_factor = kwargs.get("climate_flood_factor", "Minor")
        mock.climate_fire_factor = kwargs.get("climate_fire_factor", "Minimal")
        mock.photo_s3_paths = kwargs.get("photo_s3_paths", [])
        mock.id = kwargs.get("id", 1)
        mock.loaded_at = kwargs.get("loaded_at")
        return mock

    def test_deterministic(self):
        s1 = self._make_staging()
        s2 = self._make_staging()
        assert compute_staging_hash(s1) == compute_staging_hash(s2)

    def test_different_input(self):
        s1 = self._make_staging(address="123 Main St")
        s2 = self._make_staging(address="456 Oak Ave")
        assert compute_staging_hash(s1) != compute_staging_hash(s2)

    def test_excludes_id_and_loaded_at(self):
        s1 = self._make_staging(id=1, loaded_at="2024-01-01")
        s2 = self._make_staging(id=999, loaded_at="2025-12-31")
        assert compute_staging_hash(s1) == compute_staging_hash(s2)


# ---------------------------------------------------------------------------
# TestTransformListing
# ---------------------------------------------------------------------------
class TestTransformListing:
    def _make_staging(self, **kwargs):
        mock = MagicMock()
        mock.id = kwargs.get("id", 1)
        mock.address = kwargs.get("address", "123 Main St")
        mock.city = kwargs.get("city", "Cary")
        mock.state = kwargs.get("state", "NC")
        mock.zip_code = kwargs.get("zip_code", "27513")
        mock.listing_status = kwargs.get("listing_status", "Sold")
        mock.sold_date = kwargs.get("sold_date", "January 15, 2024")
        mock.sold_price = kwargs.get("sold_price", "$500,000")
        mock.listing_price = kwargs.get("listing_price", "$510,000")
        mock.beds = kwargs.get("beds", 3)
        mock.baths = kwargs.get("baths", 2.5)
        mock.sqft = kwargs.get("sqft", 2000)
        mock.description = kwargs.get("description", "Nice home")
        mock.year_built = kwargs.get("year_built", 2005)
        mock.lot_size = kwargs.get("lot_size", "0.25 Acres")
        mock.price_per_sqft = kwargs.get("price_per_sqft", "$250")
        mock.listing_agent = kwargs.get("listing_agent", "Agent A")
        mock.listing_brokerage = kwargs.get("listing_brokerage", "Broker A")
        mock.buying_agent = kwargs.get("buying_agent")
        mock.buying_brokerage = kwargs.get("buying_brokerage")
        mock.redfin_estimate = kwargs.get("redfin_estimate", "$490,000")
        mock.sale_history = kwargs.get("sale_history", [])
        mock.tax_history = kwargs.get("tax_history", [])
        mock.property_details = kwargs.get("property_details", {})
        mock.schools = kwargs.get("schools", [])
        mock.climate_flood_factor = kwargs.get("climate_flood_factor", "Minor")
        mock.climate_fire_factor = kwargs.get("climate_fire_factor", "Minimal")
        mock.photo_s3_paths = kwargs.get("photo_s3_paths", [])
        mock.loaded_at = None
        return mock

    def test_skips_no_address(self):
        session = MagicMock()
        staging = self._make_staging(address=None)
        result = transform_listing(session, staging)
        assert result is False

    def test_skips_unchanged_hash(self):
        staging = self._make_staging()
        existing = MagicMock()
        existing.staging_hash = compute_staging_hash(staging)
        existing.location = "some_location"

        session = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = existing

        result = transform_listing(session, staging, geocode_fn=lambda _: None)
        assert result is False

    def test_transforms_new_listing(self):
        staging = self._make_staging()

        session = MagicMock()
        # First call: PropertyDetail lookup returns None (new property)
        # Second call: PropertyValuation lookup returns None
        session.execute.return_value.scalar_one_or_none.return_value = None

        geocode_fn = MagicMock(return_value=(35.79, -78.78))

        with patch("geoalchemy2.shape.from_shape", return_value="mocked_geom"):
            result = transform_listing(session, staging, geocode_fn=geocode_fn)

        assert result is True
        session.add.assert_called()
        geocode_fn.assert_called_once()


# ---------------------------------------------------------------------------
# TestTransformAllListings
# ---------------------------------------------------------------------------
class TestTransformAllListings:
    @patch("pricepoint.data.housing.redfin_transformer.SessionLocal")
    @patch("pricepoint.data.housing.redfin_transformer.transform_listing")
    def test_batch_processing(self, mock_transform, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session

        # Return 2 staging IDs
        session.execute.return_value.scalars.return_value.all.return_value = [1, 2]

        # Mock the batch query to return 2 staging records
        staging1 = MagicMock()
        staging1.id = 1
        staging2 = MagicMock()
        staging2.id = 2
        session.execute.return_value.scalars.return_value.all.side_effect = [
            [1, 2],
            [staging1, staging2],
        ]

        mock_transform.side_effect = [True, False]

        result = transform_all_listings(batch_size=100)
        assert result["transformed"] == 1
        assert result["skipped"] == 1
        assert result["errors"] == 0

    @patch("pricepoint.data.housing.redfin_transformer.SessionLocal")
    @patch("pricepoint.data.housing.redfin_transformer.transform_listing")
    def test_error_counting(self, mock_transform, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session

        staging1 = MagicMock()
        staging1.id = 1
        session.execute.return_value.scalars.return_value.all.side_effect = [
            [1],
            [staging1],
        ]

        mock_transform.side_effect = ValueError("parse error")

        result = transform_all_listings(batch_size=100)
        assert result["errors"] == 1
        assert result["transformed"] == 0
