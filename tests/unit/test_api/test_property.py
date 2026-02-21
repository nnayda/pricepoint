"""Tests for the property endpoint."""

from io import BytesIO
from unittest.mock import MagicMock, patch


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
