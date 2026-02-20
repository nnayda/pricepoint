"""Tests for the points of interest endpoint with PostGIS queries."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.main import create_app


class _FakeRow:
    """Lightweight row object that supports attribute access like a SQLAlchemy Row."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


def _make_poi_row(
    poi_id="1",
    poi_name="Test POI",
    category="park",
    lat=35.79,
    lon=-78.78,
    distance_miles=0.5,
):
    """Create a mock DB row for POI query results."""
    return _FakeRow(
        poi_id=poi_id,
        poi_name=poi_name,
        category=category,
        lat=lat,
        lon=lon,
        distance_miles=distance_miles,
    )


def _make_pois_app(rows=None):
    """Create a test app with mocked DB returning the given POI rows."""
    app = create_app()
    mock_session = MagicMock()

    if rows is None:
        rows = [
            _make_poi_row(poi_id="1", poi_name="Central Park", category="park", distance_miles=0.3),
            _make_poi_row(
                poi_id="2",
                poi_name="Farmers Market",
                category="grocery",
                distance_miles=0.8,
                lat=35.791,
                lon=-78.781,
            ),
            _make_poi_row(
                poi_id="3",
                poi_name="Main Library",
                category="library",
                distance_miles=1.2,
                lat=35.792,
                lon=-78.782,
            ),
            _make_poi_row(
                poi_id="4",
                poi_name="WakeMed Hospital",
                category="medical",
                distance_miles=1.5,
                lat=35.793,
                lon=-78.783,
            ),
            _make_poi_row(
                poi_id="5",
                poi_name="Greenway Trail Park",
                category="park",
                distance_miles=1.9,
                lat=35.794,
                lon=-78.784,
            ),
        ]

    mock_result = MagicMock()
    mock_result.all.return_value = rows

    mock_session.execute.return_value = mock_result

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    return app, mock_session


@pytest.fixture
def pois_app():
    """Create a test app with mocked DB that returns POI data."""
    app, _ = _make_pois_app()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def pois_client(pois_app):
    """Test client for the POI app."""
    return TestClient(pois_app)


@pytest.fixture
def empty_pois_app():
    """Create a test app with mocked DB that returns no POIs."""
    app, _ = _make_pois_app(rows=[])
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_pois_client(empty_pois_app):
    """Test client for empty POI results."""
    return TestClient(empty_pois_app)


class TestPoisReturns200:
    def test_returns_200_with_valid_params(self, pois_client):
        """GET /api/pois with valid params returns 200."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestPoisResponseShape:
    def test_response_has_pois_key(self, pois_client):
        """Response contains the 'pois' key."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert "pois" in resp.json()

    def test_pois_is_list(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["pois"], list)

    def test_response_has_metrics(self, pois_client):
        """Response contains the 'metrics' key."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert "metrics" in resp.json()

    def test_metrics_has_required_fields(self, pois_client):
        """Metrics has total_count, categories_represented, nearest_distance_miles."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in ["total_count", "categories_represented", "nearest_distance_miles"]:
            assert field in metrics, f"Missing metrics field: {field}"


class TestPoisDataTypes:
    def test_poi_has_required_fields(self, pois_client):
        """Each POI has id, name, category, lat, lon, distance_miles, drive_minutes."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        pois = resp.json()["pois"]
        assert len(pois) > 0
        for field in [
            "id",
            "name",
            "category",
            "lat",
            "lon",
            "distance_miles",
            "drive_minutes",
        ]:
            assert field in pois[0], f"Missing POI field: {field}"

    def test_poi_id_is_string(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["id"], str)

    def test_poi_name_is_string(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["name"], str)

    def test_poi_category_is_string(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["category"], str)

    def test_poi_distance_is_number(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["distance_miles"], (int, float))

    def test_poi_drive_minutes_is_int(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert isinstance(poi["drive_minutes"], int)


class TestPoisMissingParams:
    def test_missing_all_params_returns_422(self, pois_client):
        resp = pois_client.get("/api/pois")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79})
        assert resp.status_code == 422


class TestPoisParamValidation:
    def test_lat_out_of_range_returns_422(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, pois_client):
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, pois_client):
        resp = pois_client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, pois_client):
        resp = pois_client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, pois_client):
        resp = pois_client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestPoisDefaultRadius:
    def test_default_radius_works(self, pois_client):
        """Omitting radius_miles uses default and returns 200."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, pois_client):
        resp = pois_client.get(
            "/api/pois",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestPoisWithData:
    """Tests that verify real data processing from mocked DB rows."""

    def test_poi_count_matches_rows(self, pois_client):
        """POI list should match the number of DB rows."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["pois"]) == 5

    def test_total_count_metric(self, pois_client):
        """total_count should equal the number of POIs."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["total_count"] == 5

    def test_categories_represented_metric(self, pois_client):
        """categories_represented should count distinct categories."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        # park, grocery, library, medical = 4
        assert resp.json()["metrics"]["categories_represented"] == 4

    def test_nearest_distance_metric(self, pois_client):
        """nearest_distance_miles should be the minimum distance."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["nearest_distance_miles"] == 0.3

    def test_pois_sorted_by_distance(self, pois_client):
        """POIs should be sorted by distance ascending."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        distances = [p["distance_miles"] for p in resp.json()["pois"]]
        assert distances == sorted(distances)

    def test_drive_minutes_estimated(self, pois_client):
        """drive_minutes should be ~distance * 3, minimum 1."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        # 0.3 miles * 3 = 0.9 -> round = 1
        assert poi["drive_minutes"] >= 1

    def test_poi_id_includes_category_prefix(self, pois_client):
        """POI IDs should be prefixed with uppercase category."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        poi = resp.json()["pois"][0]
        assert poi["id"].startswith("PARK-")

    def test_multiple_categories_present(self, pois_client):
        """POIs should span multiple categories."""
        resp = pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        categories = {p["category"] for p in resp.json()["pois"]}
        assert len(categories) >= 3


class TestPoisEmptyResults:
    """Tests for when no POIs are found in the area."""

    def test_empty_returns_200(self, empty_pois_client):
        """Should still return 200 with empty list."""
        resp = empty_pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_empty_pois_list(self, empty_pois_client):
        resp = empty_pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["pois"] == []

    def test_empty_metrics_zero(self, empty_pois_client):
        resp = empty_pois_client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        assert metrics["total_count"] == 0
        assert metrics["categories_represented"] == 0
        assert metrics["nearest_distance_miles"] is None


class TestPoisValkeyCaching:
    """Tests for Valkey cache integration."""

    def test_cache_hit_returns_cached_data(self):
        """When cache has data, should return it without DB query."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "pois": [
                {
                    "id": "PARK-1",
                    "name": "Cached Park",
                    "category": "park",
                    "lat": 35.79,
                    "lon": -78.78,
                    "distance_miles": 0.5,
                    "drive_minutes": 2,
                }
            ],
            "metrics": {
                "total_count": 1,
                "categories_represented": 1,
                "nearest_distance_miles": 0.5,
            },
        }
        mock_valkey.get.return_value = json.dumps(cached_response)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["pois"][0]["name"] == "Cached Park"
        # DB should not have been queried
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        """When cache misses, should query DB and write to cache."""
        app, mock_session = _make_pois_app()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None  # Cache miss

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/pois", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        # DB was queried
        assert mock_session.execute.call_count == 1
        # Cache was written
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestPoisHelperFunctions:
    """Tests for internal helper functions."""

    def test_cache_key_deterministic(self):
        """Same inputs should produce the same cache key."""
        from pricepoint.api.routes.pois import _cache_key

        k1 = _cache_key(35.79, -78.78, 2.0)
        k2 = _cache_key(35.79, -78.78, 2.0)
        assert k1 == k2

    def test_cache_key_varies_with_params(self):
        """Different inputs should produce different cache keys."""
        from pricepoint.api.routes.pois import _cache_key

        k1 = _cache_key(35.79, -78.78, 2.0)
        k2 = _cache_key(35.79, -78.78, 5.0)
        assert k1 != k2

    def test_cache_key_starts_with_prefix(self):
        """Cache key should start with 'pois:' prefix."""
        from pricepoint.api.routes.pois import _cache_key

        k = _cache_key(35.79, -78.78, 2.0)
        assert k.startswith("pois:")
