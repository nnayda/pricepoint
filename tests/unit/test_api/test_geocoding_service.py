"""Tests for the geocoding service module."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pricepoint.api.services.geocoding import (
    _build_nominatim_params,
    _build_photon_params,
    _parse_nominatim,
    _parse_photon,
    geocode_async,
    geocode_sync,
)

# ---------------------------------------------------------------------------
# Fixtures: realistic API responses
# ---------------------------------------------------------------------------

NOMINATIM_RESPONSE = [
    {
        "display_name": "Raleigh, Wake County, NC, USA",
        "lat": "35.7795897",
        "lon": "-78.6381787",
        "place_id": 12345,
        "osm_type": "relation",
        "osm_id": 67890,
        "boundingbox": ["35.6", "35.9", "-78.8", "-78.4"],
    }
]

PHOTON_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-78.6381787, 35.7795897]},
            "properties": {
                "osm_type": "R",
                "osm_id": 67890,
                "name": "Raleigh",
                "city": "Raleigh",
                "state": "North Carolina",
                "postcode": "27601",
                "country": "United States",
                "countrycode": "US",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [10.0, 50.0]},
            "properties": {
                "osm_type": "N",
                "osm_id": 11111,
                "name": "Raleigh",
                "country": "Germany",
                "countrycode": "DE",
            },
        },
    ],
}


def _make_settings(provider="nominatim", rate_limit=1.0):
    """Create a mock Settings object."""
    s = MagicMock()
    s.geocode_provider = provider
    s.geocode_url = "https://nominatim.openstreetmap.org/search"
    s.geocode_timeout = 5.0
    s.geocode_rate_limit_seconds = rate_limit
    return s


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParseNominatim:
    def test_parses_single_result(self):
        results = _parse_nominatim(NOMINATIM_RESPONSE)
        assert len(results) == 1
        r = results[0]
        assert r["display_name"] == "Raleigh, Wake County, NC, USA"
        assert r["lat"] == pytest.approx(35.7795897)
        assert r["lon"] == pytest.approx(-78.6381787)
        assert r["place_id"] == 12345
        assert r["osm_type"] == "relation"
        assert r["osm_id"] == 67890
        assert r["boundingbox"] == [35.6, 35.9, -78.8, -78.4]

    def test_parses_empty_list(self):
        assert _parse_nominatim([]) == []

    def test_missing_boundingbox(self):
        item = {
            "display_name": "Test",
            "lat": "35.0",
            "lon": "-78.0",
            "osm_type": "node",
            "osm_id": 1,
        }
        results = _parse_nominatim([item])
        assert results[0]["boundingbox"] == []
        assert results[0]["place_id"] is None


class TestParsePhoton:
    def test_parses_features_and_filters_country(self):
        results = _parse_photon(PHOTON_RESPONSE)
        # Only the US result should remain
        assert len(results) == 1
        r = results[0]
        assert r["lat"] == pytest.approx(35.7795897)
        assert r["lon"] == pytest.approx(-78.6381787)
        assert r["place_id"] is None
        assert r["boundingbox"] == []
        assert "Raleigh" in r["display_name"]

    def test_empty_features(self):
        assert _parse_photon({"features": []}) == []

    def test_missing_features_key(self):
        assert _parse_photon({}) == []

    def test_display_name_assembly(self):
        results = _parse_photon(PHOTON_RESPONSE)
        name = results[0]["display_name"]
        assert "Raleigh" in name
        assert "North Carolina" in name

    def test_display_name_housenumber_before_street(self):
        """House number should be combined with street as the first address part."""
        data = {
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-78.8, 35.7]},
                    "properties": {
                        "osm_type": "N",
                        "osm_id": 99999,
                        "housenumber": "104",
                        "street": "Tamarak Wood Court",
                        "city": "Cary",
                        "state": "North Carolina",
                        "postcode": "27513",
                        "country": "United States",
                        "countrycode": "US",
                    },
                }
            ],
        }
        results = _parse_photon(data)
        assert len(results) == 1
        dn = results[0]["display_name"]
        assert dn.startswith("104 Tamarak Wood Court")
        assert "Cary" in dn
        # The house number must appear before the street name
        assert dn.index("104") < dn.index("Tamarak")

    def test_display_name_street_without_housenumber(self):
        """Street-only results should still produce a valid display name."""
        data = {
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-78.8, 35.7]},
                    "properties": {
                        "osm_type": "W",
                        "osm_id": 88888,
                        "street": "Main Street",
                        "city": "Raleigh",
                        "state": "North Carolina",
                        "countrycode": "US",
                    },
                }
            ],
        }
        results = _parse_photon(data)
        assert results[0]["display_name"].startswith("Main Street")

    def test_display_name_name_differs_from_street(self):
        """POI name should appear before the street address."""
        data = {
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-78.6, 35.8]},
                    "properties": {
                        "osm_type": "N",
                        "osm_id": 77777,
                        "name": "Starbucks",
                        "housenumber": "200",
                        "street": "Fayetteville St",
                        "city": "Raleigh",
                        "state": "North Carolina",
                        "countrycode": "US",
                    },
                }
            ],
        }
        results = _parse_photon(data)
        dn = results[0]["display_name"]
        assert dn.startswith("Starbucks")
        assert "200 Fayetteville St" in dn


# ---------------------------------------------------------------------------
# Parameter builder tests
# ---------------------------------------------------------------------------


class TestBuildParams:
    def test_nominatim_params_basic(self):
        params = _build_nominatim_params("Raleigh", 5, None, None)
        assert params["q"] == "Raleigh"
        assert params["format"] == "json"
        assert params["limit"] == 5
        assert params["countrycodes"] == "us"
        assert "viewbox" not in params

    def test_nominatim_params_with_bias(self):
        params = _build_nominatim_params("Raleigh", 5, 35.79, -78.78)
        assert "viewbox" in params
        assert params["bounded"] == 0

    def test_photon_params_basic(self):
        params = _build_photon_params("Raleigh", 5, None, None)
        assert params["q"] == "Raleigh"
        assert params["limit"] == 5
        assert params["lang"] == "en"
        assert "lat" not in params

    def test_photon_params_with_bias(self):
        params = _build_photon_params("Raleigh", 5, 35.79, -78.78)
        assert params["lat"] == 35.79
        assert params["lon"] == -78.78


# ---------------------------------------------------------------------------
# geocode_async tests
# ---------------------------------------------------------------------------


class TestGeocodeAsync:
    @pytest.mark.asyncio
    async def test_nominatim_success(self):
        mock_resp = httpx.Response(
            200,
            json=NOMINATIM_RESPONSE,
            request=httpx.Request("GET", "https://example.com"),
        )
        with patch("pricepoint.api.services.geocoding.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocode_async("Raleigh", settings=_make_settings("nominatim"))

        assert len(results) == 1
        assert results[0]["display_name"] == "Raleigh, Wake County, NC, USA"

    @pytest.mark.asyncio
    async def test_photon_success(self):
        mock_resp = httpx.Response(
            200,
            json=PHOTON_RESPONSE,
            request=httpx.Request("GET", "https://example.com"),
        )
        with patch("pricepoint.api.services.geocoding.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocode_async("Raleigh", settings=_make_settings("photon"))

        assert len(results) == 1
        assert results[0]["place_id"] is None

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self):
        with patch("pricepoint.api.services.geocoding.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocode_async("Raleigh", settings=_make_settings())

        assert results == []

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        with patch("pricepoint.api.services.geocoding.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            results = await geocode_async("Raleigh", settings=_make_settings())

        assert results == []


# ---------------------------------------------------------------------------
# geocode_sync tests
# ---------------------------------------------------------------------------


class TestGeocodeSync:
    @patch("pricepoint.api.services.geocoding.time.sleep")
    @patch("pricepoint.api.services.geocoding.httpx.get")
    def test_nominatim_success(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = NOMINATIM_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        results = geocode_sync("Raleigh", settings=_make_settings("nominatim", rate_limit=1.0))
        assert len(results) == 1
        mock_sleep.assert_called_once_with(1.0)

    @patch("pricepoint.api.services.geocoding.time.sleep")
    @patch("pricepoint.api.services.geocoding.httpx.get")
    def test_photon_success(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = PHOTON_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        results = geocode_sync("Raleigh", settings=_make_settings("photon", rate_limit=0.0))
        assert len(results) == 1
        assert results[0]["place_id"] is None
        mock_sleep.assert_not_called()

    @patch("pricepoint.api.services.geocoding.time.sleep")
    @patch("pricepoint.api.services.geocoding.httpx.get")
    def test_rate_limit_applied(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geocode_sync("Test", settings=_make_settings(rate_limit=0.5))
        mock_sleep.assert_called_once_with(0.5)

    @patch("pricepoint.api.services.geocoding.time.sleep")
    @patch("pricepoint.api.services.geocoding.httpx.get")
    def test_no_rate_limit_when_zero(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geocode_sync("Test", settings=_make_settings(rate_limit=0.0))
        mock_sleep.assert_not_called()

    @patch("pricepoint.api.services.geocoding.time.sleep")
    @patch("pricepoint.api.services.geocoding.httpx.get")
    def test_error_returns_empty(self, mock_get, mock_sleep):
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        results = geocode_sync("Test", settings=_make_settings())
        assert results == []

    @patch("pricepoint.api.services.geocoding.time.sleep")
    @patch("pricepoint.api.services.geocoding.httpx.get")
    def test_bias_coords_passed(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = NOMINATIM_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geocode_sync("Test", bias_lat=35.79, bias_lon=-78.78, settings=_make_settings())
        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs["params"]
        assert "viewbox" in params
