"""Tests for the property endpoint."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from pricepoint.api.routes.property import _build_exterior, _build_interior, _build_utilities


class TestBuildInteriorFromDetails:
    """Test _build_interior extracts fields from property_details JSON."""

    def test_extracts_flooring_and_appliances(self):
        prop = MagicMock()
        prop.property_details = {
            "flooring": "Hardwood, Tile, Carpet",
            "appliances": "Dishwasher, Microwave",
            "heating": "Forced Air",
            "cooling": "Central Air",
        }
        prop.has_fireplace = True
        result = _build_interior(prop)
        assert result.flooring == ["Hardwood", "Tile", "Carpet"]
        assert result.appliances == ["Dishwasher", "Microwave"]
        assert result.heating == "Forced Air"
        assert result.cooling == "Central Air"
        assert result.fireplace is True

    def test_falls_back_to_unknown_when_empty(self):
        prop = MagicMock()
        prop.property_details = {}
        prop.has_fireplace = False
        result = _build_interior(prop)
        assert result.flooring == []
        assert result.appliances == []
        assert result.heating == "Unknown"
        assert result.cooling == "Unknown"
        assert result.fireplace is False

    def test_handles_none_property_details(self):
        prop = MagicMock()
        prop.property_details = None
        prop.has_fireplace = False
        result = _build_interior(prop)
        assert result.heating == "Unknown"

    def test_basement_fallback_to_basement_details(self):
        prop = MagicMock()
        prop.property_details = {"basement_details": "Walk-Out"}
        prop.has_fireplace = False
        result = _build_interior(prop)
        assert result.basement == "Walk-Out"


class TestBuildExteriorFromDetails:
    """Test _build_exterior extracts fields from property_details JSON."""

    def test_extracts_roof_and_fencing(self):
        prop = MagicMock()
        prop.property_details = {
            "roof": "Shingle",
            "fencing": "Wood Privacy",
            "foundation_details": "Crawl Space",
        }
        prop.facade_type = "Vinyl"
        prop.parking_type = "2-Car Garage"
        prop.has_private_pool = False
        prop.has_community_pool = False
        result = _build_exterior(prop)
        assert result.roof == "Shingle"
        assert result.fence == "Wood Privacy"
        assert result.foundation == "Crawl Space"
        assert result.siding == "Vinyl"
        assert result.parking == "2-Car Garage"
        assert result.pool is False

    def test_pool_true_from_community(self):
        prop = MagicMock()
        prop.property_details = {}
        prop.facade_type = None
        prop.parking_type = None
        prop.has_private_pool = False
        prop.has_community_pool = True
        result = _build_exterior(prop)
        assert result.pool is True


class TestBuildUtilities:
    """Test _build_utilities extraction."""

    def test_returns_utilities_when_present(self):
        prop = MagicMock()
        prop.property_details = {
            "water_source": "City Water",
            "sewer": "Public Sewer",
            "electric": "Duke Energy",
        }
        result = _build_utilities(prop)
        assert result is not None
        assert result.water == "City Water"
        assert result.sewer == "Public Sewer"
        assert result.electric == "Duke Energy"

    def test_returns_none_when_no_utilities(self):
        prop = MagicMock()
        prop.property_details = {}
        result = _build_utilities(prop)
        assert result is None


class TestPropertyResponseSchema:
    """Test PropertyResponse schema includes listing_id."""

    def test_listing_id_defaults_to_none(self):
        """PropertyResponse listing_id defaults to None."""
        from pricepoint.api.schemas.property import PropertyResponse

        data = PropertyResponse.model_json_schema()
        props = data.get("properties", {})
        assert "listing_id" in props
        # Default is None
        listing_id_schema = props["listing_id"]
        assert listing_id_schema.get("default") is None


class TestPropertyNotFound:
    def test_returns_404_when_not_in_db(self, client):
        """GET /api/property returns 404 when property not found."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "123 Main St"},
        )
        assert resp.status_code == 404

    def test_404_response_has_detail(self, client):
        """404 response includes detail message."""
        resp = client.get(
            "/api/property",
            params={"lat": 35.79, "lon": -78.78, "address": "123 Main St"},
        )
        assert resp.json()["detail"] == "Property not found"


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


class TestPhotoProxy:
    @patch("pricepoint.api.routes.property.boto3")
    def test_returns_image_from_s3(self, mock_boto3, client):
        """GET /api/photos/<key> streams image from S3."""
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.get_object.return_value = {
            "Body": BytesIO(b"\xff\xd8\xff\xe0fake-jpeg"),
            "ContentType": "image/jpeg",
        }
        resp = client.get("/api/photos/redfin/photos/slug/photo_0.jpeg")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert resp.headers["cache-control"] == "public, max-age=86400"

    @patch("pricepoint.api.routes.property.boto3")
    def test_returns_404_for_missing_key(self, mock_boto3, client):
        """GET /api/photos/<missing> returns 404."""
        from botocore.exceptions import ClientError

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )
        resp = client.get("/api/photos/nonexistent/photo.jpg")
        assert resp.status_code == 404
