"""Tests for the geocode endpoint."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from pricepoint.api.dependencies import get_valkey

GEOCODE_RESULT = {
    "display_name": "Raleigh, Wake County, NC, USA",
    "lat": 35.7795897,
    "lon": -78.6381787,
    "place_id": 12345,
    "osm_type": "relation",
    "osm_id": 67890,
    "boundingbox": [35.6, 35.9, -78.8, -78.4],
}

GEOCODE_RESULT_2 = {
    "display_name": "Raleigh, Durham County, NC, USA",
    "lat": 35.8,
    "lon": -78.7,
    "place_id": 54321,
    "osm_type": "way",
    "osm_id": 99999,
    "boundingbox": [35.7, 35.9, -78.8, -78.6],
}

PHOTON_RESULT = {
    "display_name": "Raleigh, North Carolina, United States",
    "lat": 35.7795897,
    "lon": -78.6381787,
    "place_id": None,
    "osm_type": "R",
    "osm_id": 67890,
    "boundingbox": [],
}


def _patch_geocode_async(results=None):
    """Patch geocode_async to return controlled results."""
    if results is None:
        results = [GEOCODE_RESULT]
    return patch(
        "pricepoint.api.routes.geocode.geocode_async",
        new_callable=AsyncMock,
        return_value=results,
    )


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


@pytest.mark.usefixtures("_no_valkey")
class TestGeocodeReturnsResults:
    def test_geocode_returns_results(self, client):
        """Mock geocode_async and verify response shape."""
        with _patch_geocode_async():
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

    def test_geocode_multiple_results(self, client):
        """Multiple results are all returned."""
        with _patch_geocode_async([GEOCODE_RESULT, GEOCODE_RESULT_2]):
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        data = resp.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["display_name"] == "Raleigh, Wake County, NC, USA"
        assert data["results"][1]["display_name"] == "Raleigh, Durham County, NC, USA"
        assert data["results"][1]["lat"] == 35.8
        assert data["results"][1]["place_id"] == 54321

    def test_geocode_empty_results(self, client):
        """Provider returning zero results gives 200 with empty list."""
        with _patch_geocode_async([]):
            resp = client.get("/api/geocode", params={"q": "xyznonexistent"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["cached"] is False

    def test_geocode_photon_style_result(self, client):
        """Photon results with place_id=None are accepted."""
        with _patch_geocode_async([PHOTON_RESULT]):
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert result["place_id"] is None
        assert result["boundingbox"] == []


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
class TestGeocodePassesLimit:
    def test_geocode_passes_limit_to_service(self, client):
        """Verify limit is passed to geocode_async."""
        with _patch_geocode_async([]) as mock_fn:
            client.get("/api/geocode", params={"q": "Raleigh", "limit": 3})
            mock_fn.assert_called_once_with("Raleigh", limit=3)


class TestGeocodeCachesResults:
    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_miss_calls_service_and_writes_cache(self, client, mock_valkey):
        """On cache miss, geocode_async is called and result is cached."""
        with _patch_geocode_async():
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        assert resp.json()["cached"] is False
        mock_valkey.get.assert_called_once_with("geocode:raleigh:5")
        mock_valkey.set.assert_called_once()
        set_args = mock_valkey.set.call_args
        assert set_args.args[0] == "geocode:raleigh:5"
        assert set_args.kwargs["ex"] == 2592000

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_hit_skips_service(self, client, mock_valkey):
        """On cache hit, geocode_async is NOT called and cached=True."""
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

        with _patch_geocode_async() as mock_fn:
            resp = client.get("/api/geocode", params={"q": "Raleigh"})
            mock_fn.assert_not_called()

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is True
        assert len(data["results"]) == 1

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_hit_with_null_place_id(self, client, mock_valkey):
        """Cached Photon result with place_id=None deserializes correctly."""
        cached_data = json.dumps(
            [
                {
                    "display_name": "Raleigh, NC",
                    "lat": 35.78,
                    "lon": -78.64,
                    "place_id": None,
                    "osm_type": "R",
                    "osm_id": 2,
                    "boundingbox": [],
                }
            ]
        )
        mock_valkey.get.return_value = cached_data

        with _patch_geocode_async():
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert result["place_id"] is None
        assert result["boundingbox"] == []

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_hit_returns_correct_data(self, client, mock_valkey):
        """Cached data is deserialized and returned with correct field values."""
        cached_data = json.dumps(
            [
                {
                    "display_name": "123 Main St, Raleigh, NC",
                    "lat": 35.78,
                    "lon": -78.64,
                    "place_id": 42,
                    "osm_type": "way",
                    "osm_id": 100,
                    "boundingbox": [35.0, 36.0, -79.0, -78.0],
                }
            ]
        )
        mock_valkey.get.return_value = cached_data

        with _patch_geocode_async():
            resp = client.get("/api/geocode", params={"q": "123 Main"})

        result = resp.json()["results"][0]
        assert result["display_name"] == "123 Main St, Raleigh, NC"
        assert result["lat"] == 35.78
        assert result["lon"] == -78.64
        assert result["place_id"] == 42

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_stores_valid_json(self, client, mock_valkey):
        """Data written to cache is valid JSON that round-trips correctly."""
        with _patch_geocode_async():
            client.get("/api/geocode", params={"q": "Raleigh"})

        stored_json = mock_valkey.set.call_args.args[1]
        parsed = json.loads(stored_json)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["display_name"] == "Raleigh, Wake County, NC, USA"
        assert parsed[0]["lat"] == 35.7795897
        assert parsed[0]["lon"] == -78.6381787

    @pytest.mark.usefixtures("_with_valkey")
    def test_empty_results_not_cached(self, client, mock_valkey):
        """Empty results are NOT written to cache."""
        with _patch_geocode_async([]):
            client.get("/api/geocode", params={"q": "xyznonexistent"})

        mock_valkey.set.assert_not_called()

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_ttl_is_30_days(self, client, mock_valkey):
        """Cache TTL is 2592000 seconds (30 days)."""
        with _patch_geocode_async():
            client.get("/api/geocode", params={"q": "Raleigh"})

        assert mock_valkey.set.call_args.kwargs["ex"] == 2592000


class TestGeocodeCacheKeyNormalization:
    """Cache keys are normalized so variant queries share a cache entry."""

    @pytest.mark.usefixtures("_with_valkey")
    def test_uppercase_query_normalizes_to_lowercase_key(self, client, mock_valkey):
        """'RALEIGH' produces cache key 'geocode:raleigh:5'."""
        with _patch_geocode_async():
            client.get("/api/geocode", params={"q": "RALEIGH"})

        mock_valkey.get.assert_called_once_with("geocode:raleigh:5")

    @pytest.mark.usefixtures("_with_valkey")
    def test_whitespace_trimmed_in_key(self, client, mock_valkey):
        """Leading/trailing whitespace is stripped from cache key."""
        with _patch_geocode_async():
            client.get("/api/geocode", params={"q": "  Raleigh  "})

        mock_valkey.get.assert_called_once_with("geocode:raleigh:5")

    @pytest.mark.usefixtures("_with_valkey")
    def test_custom_limit_included_in_key(self, client, mock_valkey):
        """Different limit values produce different cache keys."""
        with _patch_geocode_async():
            client.get("/api/geocode", params={"q": "Raleigh", "limit": 3})

        mock_valkey.get.assert_called_once_with("geocode:raleigh:3")


class TestGeocodeCacheFailover:
    """Valkey failures don't break the endpoint."""

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_read_failure_falls_through_to_service(self, client, mock_valkey):
        """Exception during cache read still calls geocode_async and returns results."""
        mock_valkey.get.side_effect = ConnectionError("Redis down")

        with _patch_geocode_async():
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        assert resp.json()["cached"] is False
        assert len(resp.json()["results"]) == 1

    @pytest.mark.usefixtures("_with_valkey")
    def test_cache_write_failure_still_returns_results(self, client, mock_valkey):
        """Exception during cache write still returns results."""
        mock_valkey.set.side_effect = ConnectionError("Redis down")

        with _patch_geocode_async():
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1


@pytest.mark.usefixtures("_no_valkey")
class TestGeocodeWorksWithoutValkey:
    def test_geocode_works_without_valkey(self, client):
        """When valkey is None, geocode_async is still called and results returned."""
        with _patch_geocode_async():
            resp = client.get("/api/geocode", params={"q": "Raleigh"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["cached"] is False
        assert len(data["results"]) == 1


class TestGeocodeLimitCapped:
    @pytest.mark.usefixtures("_no_valkey")
    def test_geocode_limit_capped(self, client):
        """limit > 10 gets capped to 10."""
        with _patch_geocode_async([]) as mock_fn:
            client.get("/api/geocode", params={"q": "Raleigh", "limit": 50})
            mock_fn.assert_called_once_with("Raleigh", limit=10)
