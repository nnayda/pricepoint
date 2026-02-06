"""Tests for the property endpoint."""


class TestPropertyReturns200:
    def test_returns_200_with_valid_params(self, client):
        """GET /api/property with valid params returns 200."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "123 Main St"},
        )
        assert resp.status_code == 200

    def test_response_is_json(self, client):
        """Response body is valid JSON."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "123 Main St"},
        )
        data = resp.json()
        assert isinstance(data, dict)


class TestPropertyResponseShape:
    def test_response_has_all_top_level_keys(self, client):
        """Response contains all expected top-level sections."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "123 Main St"},
        )
        data = resp.json()
        expected_keys = [
            "details",
            "valuation",
            "interior",
            "exterior",
            "financial",
            "schools",
            "sale_history",
            "tax_history",
            "climate_risk",
        ]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_details_has_required_fields(self, client):
        """Details section contains all expected fields."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test Addr"},
        )
        details = resp.json()["details"]
        for field in [
            "address",
            "city",
            "state",
            "zip_code",
            "lat",
            "lon",
            "bedrooms",
            "bathrooms",
            "sqft",
            "lot_size_sqft",
            "year_built",
            "property_type",
            "stories",
            "garage_spaces",
            "description",
            "highlights",
            "images",
        ]:
            assert field in details, f"Missing details field: {field}"

    def test_valuation_has_required_fields(self, client):
        """Valuation section contains all expected fields."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        valuation = resp.json()["valuation"]
        for field in [
            "predicted_value",
            "confidence_interval_low",
            "confidence_interval_high",
            "model_version",
            "prediction_date",
        ]:
            assert field in valuation, f"Missing valuation field: {field}"

    def test_schools_is_list(self, client):
        """Schools section is a list."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["schools"], list)

    def test_sale_history_is_list(self, client):
        """Sale history section is a list."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["sale_history"], list)

    def test_tax_history_is_list(self, client):
        """Tax history section is a list."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["tax_history"], list)


class TestPropertyAddressEchoedBack:
    def test_address_echoed_back(self, client):
        """Address passed as query param is returned in details."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "456 Oak Ave"},
        )
        assert resp.json()["details"]["address"] == "456 Oak Ave"

    def test_lat_lon_echoed_back(self, client):
        """Lat/lon passed as query params are returned in details."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.5, "lon": -78.5, "address": "Test"},
        )
        details = resp.json()["details"]
        assert details["lat"] == 35.5
        assert details["lon"] == -78.5


class TestPropertyDataTypes:
    def test_bedrooms_is_int(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["details"]["bedrooms"], int)

    def test_bathrooms_is_number(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["details"]["bathrooms"], (int, float))

    def test_sqft_is_int(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["details"]["sqft"], int)

    def test_predicted_value_is_float(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert isinstance(resp.json()["valuation"]["predicted_value"], (int, float))

    def test_highlights_is_list_of_strings(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        highlights = resp.json()["details"]["highlights"]
        assert isinstance(highlights, list)
        assert all(isinstance(h, str) for h in highlights)

    def test_images_have_url_and_alt(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        images = resp.json()["details"]["images"]
        assert len(images) > 0
        for img in images:
            assert "url" in img
            assert "alt" in img

    def test_school_has_expected_fields(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        schools = resp.json()["schools"]
        assert len(schools) > 0
        school = schools[0]
        for field in [
            "name",
            "school_type",
            "rating",
            "distance_miles",
            "drive_minutes",
        ]:
            assert field in school

    def test_sale_history_entry_has_fields(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        entries = resp.json()["sale_history"]
        assert len(entries) > 0
        entry = entries[0]
        for field in ["date", "price", "event_type"]:
            assert field in entry

    def test_tax_history_entry_has_fields(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        entries = resp.json()["tax_history"]
        assert len(entries) > 0
        entry = entries[0]
        for field in ["year", "assessed_value", "tax_amount"]:
            assert field in entry

    def test_climate_risk_has_fields(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        risk = resp.json()["climate_risk"]
        for field in ["flood_risk", "flood_score", "fire_risk", "fire_score"]:
            assert field in risk


class TestPropertyMissingParams:
    def test_missing_all_params_returns_422(self, client):
        """Missing all required params returns 422."""
        resp = client.get("/api/property")
        assert resp.status_code == 422

    def test_missing_address_returns_422(self, client):
        """Missing address param returns 422."""
        resp = client.get("/api/property", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, client):
        """Missing lat param returns 422."""
        resp = client.get("/api/property", params={"lon": -78.78, "address": "Test"})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        """Missing lon param returns 422."""
        resp = client.get("/api/property", params={"lat": 35.79, "address": "Test"})
        assert resp.status_code == 422

    def test_empty_address_returns_422(self, client):
        """Empty address string returns 422."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": ""},
        )
        assert resp.status_code == 422


class TestPropertyParamValidation:
    def test_lat_out_of_range_returns_422(self, client):
        """Lat > 90 returns 422."""
        resp = client.get(
            "/api/property",
            params={"lat": 91.0, "lon": -78.78, "address": "Test"},
        )
        assert resp.status_code == 422

    def test_lat_below_range_returns_422(self, client):
        """Lat < -90 returns 422."""
        resp = client.get(
            "/api/property",
            params={"lat": -91.0, "lon": -78.78, "address": "Test"},
        )
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        """Lon > 180 returns 422."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": 181.0, "address": "Test"},
        )
        assert resp.status_code == 422

    def test_lon_below_range_returns_422(self, client):
        """Lon < -180 returns 422."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -181.0, "address": "Test"},
        )
        assert resp.status_code == 422


class TestPropertyRealisticData:
    def test_bedrooms_in_realistic_range(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        bedrooms = resp.json()["details"]["bedrooms"]
        assert 0 < bedrooms < 20

    def test_sqft_in_realistic_range(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        sqft = resp.json()["details"]["sqft"]
        assert 100 < sqft < 50000

    def test_predicted_value_is_positive(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        val = resp.json()["valuation"]["predicted_value"]
        assert val > 0

    def test_confidence_interval_ordered(self, client):
        """Low CI is less than high CI."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        v = resp.json()["valuation"]
        assert v["confidence_interval_low"] < v["confidence_interval_high"]

    def test_school_ratings_in_range(self, client):
        """School ratings should be between 1 and 10."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        for school in resp.json()["schools"]:
            assert 1 <= school["rating"] <= 10

    def test_has_multiple_schools(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert len(resp.json()["schools"]) >= 3

    def test_has_multiple_sale_history_entries(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert len(resp.json()["sale_history"]) >= 2

    def test_has_multiple_tax_history_entries(self, client):
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        assert len(resp.json()["tax_history"]) >= 5

    def test_has_primary_image(self, client):
        """At least one image should be marked as primary."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "Test"},
        )
        images = resp.json()["details"]["images"]
        assert any(img.get("is_primary") for img in images)
