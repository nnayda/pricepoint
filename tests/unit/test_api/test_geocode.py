"""Tests for the geocode endpoint."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from pricepoint.api.dependencies import get_valkey

NOMINATIM_RESULT = {
    "display_name": "Raleigh, Wake County, NC, USA",
    "lat": "35.7795897",
    "lon": "-78.6381787",
    "place_id": 12345,
    "osm_type": "relation",
    "osm_id": 67890,
    "boundingbox": ["35.6", "35.9", "-78.8", "-78.4"],
}


@pytest.fixture
def _no_valkey(app):
    """Override valkey dependency to return None."""
    app.dependency_overrides[get_valkey] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_valkey():
    """Create a mock Valkey/Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    return mock


@pytest.fixture
def _with_valkey(app, mock_valkey):
    """Override valkey dependency with a mock."""

    async def _override():
        yield mock_valkey

    app.dependency_overrides[get_valkey] = _override
    yield
    app.dependency_overrides.clear()


def _mock_nominatim_response(results=None, status_code=200):
    """Build a mock httpx.Response for Nominatim."""
    if results is None:
        results = [NOMINATIM_RESULT]
    return httpx.Response(
        status_code=status_code,
        json=results,
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )


@pytest.mark.usefixtures("_no_valkey")
class TestGeocodeReturnsResults:
    def test_geocode_returns_results(self, client):
        """Mock httpx and verify response shape."""
        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_nominatim_response()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["display_name"] == "Raleigh, Wake County, NC, USA"
        assert result["lat"] == 35.7795897
        assert result["lon"] == -78.6381787
        assert result["place_id"] == 12345
        assert result["osm_type"] == "relation"
        assert result["osm_id"] == 67890
        assert result["boundingbox"] == [35.6, 35.9, -78.8, -78.4]


class TestGeocodeEmptyQuery:
    def test_geocode_empty_query(self, client):
        """Empty q should return 422."""
        resp = client.get("/api/geocode", params={"q": ""})
        assert resp.status_code == 422

    def test_geocode_missing_query(self, client):
        """Missing q should return 422."""
        resp = client.get("/api/geocode")
        assert resp.status_code == 422


class TestGeocodeShortQuery:
    def test_geocode_short_query(self, client):
        """q='a' (single char) should return 422 due to min_length=2."""
        resp = client.get("/api/geocode", params={"q": "a"})
        assert resp.status_code == 422


@pytest.mark.usefixtures("_no_valkey")
class TestGeocodePassesParams:
    def test_geocode_passes_params_to_nominatim(self, client):
        """Verify countrycodes, limit, and format are passed to Nominatim."""
        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_nominatim_response()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            client.get("/api/geocode", params={"q": "Raleigh", "limit": 3})

            call_kwargs = mock_client.get.call_args
            params = call_kwargs.kwargs["params"]
            assert params["countrycodes"] == "us"
            assert params["format"] == "json"
            assert params["limit"] == 3
            assert params["q"] == "Raleigh"
            headers = call_kwargs.kwargs["headers"]
            assert headers["User-Agent"] == "PricePoint/0.1.0"


@pytest.mark.usefixtures("_no_valkey")
class TestGeocodeNominatimTimeout:
    def test_geocode_nominatim_timeout(self, client):
        """Nominatim timeout should return 200 with empty results (graceful 502)."""
        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["cached"] is False


class TestGeocodeCachesResults:
    @pytest.mark.usefixtures("_with_valkey")
    def test_geocode_cache_miss_then_write(self, client, mock_valkey):
        """On cache miss, Nominatim is called and result is cached."""
        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_nominatim_response()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        assert resp.json()["cached"] is False
        mock_valkey.get.assert_called_once_with("geocode:raleigh:5")
        mock_valkey.set.assert_called_once()
        set_args = mock_valkey.set.call_args
        assert set_args.args[0] == "geocode:raleigh:5"
        assert set_args.kwargs["ex"] == 86400

    @pytest.mark.usefixtures("_with_valkey")
    def test_geocode_cache_hit(self, client, mock_valkey):
        """On cache hit, Nominatim is NOT called and cached=True."""
        cached_data = json.dumps(
            [
                {
                    "display_name": "Raleigh, NC",
                    "lat": 35.78,
                    "lon": -78.64,
                    "place_id": 1,
                    "osm_type": "relation",
                    "osm_id": 2,
                    "boundingbox": [35.0, 36.0, -79.0, -78.0],
                }
            ]
        )
        mock_valkey.get.return_value = cached_data

        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.get("/api/geocode", params={"q": "Raleigh"})

            mock_client.get.assert_not_called()

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is True
        assert len(data["results"]) == 1


@pytest.mark.usefixtures("_no_valkey")
class TestGeocodeWorksWithoutValkey:
    def test_geocode_works_without_valkey(self, client):
        """When valkey is None, Nominatim is still called and results returned."""
        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_nominatim_response()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert len(data["results"]) == 1


class TestGeocodeLimitCapped:
    @pytest.mark.usefixtures("_no_valkey")
    def test_geocode_limit_capped(self, client):
        """limit > 10 gets capped to 10."""
        with patch("pricepoint.api.routes.geocode.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_nominatim_response()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            client.get("/api/geocode", params={"q": "Raleigh", "limit": 50})

            params = mock_client.get.call_args.kwargs["params"]
            assert params["limit"] == 10
