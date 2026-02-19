"""Tests for the greenspace endpoint with real PostGIS query mocking."""

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


def _make_park_row(
    feature_id="1",
    name="Test Park",
    feature_type="park",
    lat=35.79,
    lon=-78.78,
    distance_miles=0.5,
    acreage=50.0,
    source="wake",
):
    return _FakeRow(
        feature_id=feature_id,
        name=name,
        feature_type=feature_type,
        lat=lat,
        lon=lon,
        distance_miles=distance_miles,
        acreage=acreage,
        source=source,
    )


def _make_greenway_row(
    feature_id="1",
    name="Test Greenway",
    feature_type="trail",
    lat=35.79,
    lon=-78.78,
    distance_miles=0.3,
    source="raleigh",
):
    return _FakeRow(
        feature_id=feature_id,
        name=name,
        feature_type=feature_type,
        lat=lat,
        lon=lon,
        distance_miles=distance_miles,
        source=source,
    )


@pytest.fixture
def greenspace_app():
    """Create a test app with mocked DB returning park and greenway data."""
    app = create_app()
    mock_session = MagicMock()

    park_rows = [
        _make_park_row(
            feature_id="10",
            name="Bond Metro Park",
            distance_miles=0.6,
            acreage=310.0,
            source="wake",
        ),
        _make_park_row(
            feature_id="20",
            name="Annie Jones Park",
            distance_miles=0.5,
            acreage=56.0,
            source="raleigh",
        ),
        _make_park_row(
            feature_id="30",
            name="Cary Dog Park",
            distance_miles=1.5,
            acreage=4.5,
            source="cary",
        ),
    ]

    greenway_rows = [
        _make_greenway_row(
            feature_id="100",
            name="Black Creek Greenway",
            distance_miles=0.3,
            source="wake",
        ),
        _make_greenway_row(
            feature_id="200",
            name="Hinshaw Greenway",
            distance_miles=0.9,
            source="raleigh",
        ),
    ]

    mock_park_result = MagicMock()
    mock_park_result.all.return_value = park_rows

    mock_greenway_result = MagicMock()
    mock_greenway_result.all.return_value = greenway_rows

    mock_session.execute.side_effect = [mock_park_result, mock_greenway_result]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def greenspace_client(greenspace_app):
    """Test client for the greenspace app."""
    return TestClient(greenspace_app)


@pytest.fixture
def empty_greenspace_app():
    """Create a test app with mocked DB returning no greenspace data."""
    app = create_app()
    mock_session = MagicMock()

    mock_park_result = MagicMock()
    mock_park_result.all.return_value = []

    mock_greenway_result = MagicMock()
    mock_greenway_result.all.return_value = []

    mock_session.execute.side_effect = [mock_park_result, mock_greenway_result]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_greenspace_client(empty_greenspace_app):
    """Test client for empty greenspace results."""
    return TestClient(empty_greenspace_app)


class TestGreenspaceReturns200:
    def test_returns_200_with_valid_params(self, greenspace_client):
        """GET /api/greenspace with valid params returns 200."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, greenspace_client):
        """Response body is valid JSON."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestGreenspaceResponseShape:
    def test_response_has_features_and_metrics(self, greenspace_client):
        """Response contains 'features' and 'metrics' keys."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert "features" in data
        assert "metrics" in data

    def test_features_is_list(self, greenspace_client):
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["features"], list)

    def test_metrics_is_dict(self, greenspace_client):
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"], dict)

    def test_feature_has_required_fields(self, greenspace_client):
        """Each feature has id, name, feature_type, lat, lon, distance_miles."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        assert len(features) > 0
        for field in ["id", "name", "feature_type", "lat", "lon", "distance_miles"]:
            assert field in features[0], f"Missing feature field: {field}"

    def test_metrics_has_required_fields(self, greenspace_client):
        """Metrics has parks_within_1mi, nearest_park_miles, total_green_acres_1mi, z_score."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in [
            "parks_within_1mi",
            "nearest_park_miles",
            "total_green_acres_1mi",
            "greenspace_z_score",
        ]:
            assert field in metrics, f"Missing metric field: {field}"


class TestGreenspaceWithData:
    """Tests that verify real data processing from mocked DB rows."""

    def test_total_features_count(self, greenspace_client):
        """Should return 3 parks + 2 greenways = 5 features."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) == 5

    def test_park_features_have_acreage(self, greenspace_client):
        """Park features should include acreage."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        parks = [f for f in resp.json()["features"] if f["feature_type"] == "park"]
        assert len(parks) == 3
        for park in parks:
            assert park["acreage"] is not None

    def test_trail_features_have_no_acreage(self, greenspace_client):
        """Trail features should have null acreage."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        trails = [f for f in resp.json()["features"] if f["feature_type"] == "trail"]
        assert len(trails) == 2
        for trail in trails:
            assert trail["acreage"] is None

    def test_parks_within_1mi_metric(self, greenspace_client):
        """Two parks are within 1 mile (0.5 and 0.6), one is at 1.5."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["parks_within_1mi"] == 2

    def test_nearest_park_miles(self, greenspace_client):
        """Nearest park is at 0.5 miles."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["nearest_park_miles"] == 0.5

    def test_total_green_acres_1mi(self, greenspace_client):
        """Parks within 1mi: 310.0 + 56.0 = 366.0 acres."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["total_green_acres_1mi"] == 366.0

    def test_features_sorted_by_distance(self, greenspace_client):
        """Features should be sorted by distance ascending."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        distances = [f["distance_miles"] for f in resp.json()["features"]]
        assert distances == sorted(distances)

    def test_feature_ids_include_source(self, greenspace_client):
        """Feature IDs should include type and source prefix."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        ids = [f["id"] for f in resp.json()["features"]]
        assert any("park-wake-" in i for i in ids)
        assert any("trail-raleigh-" in i for i in ids)

    def test_features_have_varied_types(self, greenspace_client):
        """Features should include both parks and trails."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        types = {f["feature_type"] for f in resp.json()["features"]}
        assert types == {"park", "trail"}


class TestGreenspaceEmptyResults:
    """Tests for when no greenspace features are found."""

    def test_empty_returns_200(self, empty_greenspace_client):
        """Should still return 200 with empty lists."""
        resp = empty_greenspace_client.get(
            "/api/greenspace", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.status_code == 200

    def test_empty_features(self, empty_greenspace_client):
        resp = empty_greenspace_client.get(
            "/api/greenspace", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.json()["features"] == []

    def test_empty_metrics_zeros(self, empty_greenspace_client):
        resp = empty_greenspace_client.get(
            "/api/greenspace", params={"lat": 35.79, "lon": -78.78}
        )
        metrics = resp.json()["metrics"]
        assert metrics["parks_within_1mi"] == 0
        assert metrics["nearest_park_miles"] == 0.0
        assert metrics["total_green_acres_1mi"] == 0.0


class TestGreenspaceParamValidation:
    def test_missing_lat_returns_422(self, greenspace_client):
        resp = greenspace_client.get("/api/greenspace", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, greenspace_client):
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79})
        assert resp.status_code == 422

    def test_missing_all_params_returns_422(self, greenspace_client):
        resp = greenspace_client.get("/api/greenspace")
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, greenspace_client):
        resp = greenspace_client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, greenspace_client):
        resp = greenspace_client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, greenspace_client):
        resp = greenspace_client.get(
            "/api/greenspace",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestGreenspaceValkeyCaching:
    """Tests for Valkey cache integration."""

    def test_cache_hit_returns_cached_data(self):
        """When cache has data, should return without DB query."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "features": [
                {
                    "id": "park-wake-1",
                    "name": "Cached Park",
                    "feature_type": "park",
                    "lat": 35.79,
                    "lon": -78.78,
                    "distance_miles": 0.5,
                    "acreage": 100.0,
                }
            ],
            "metrics": {
                "parks_within_1mi": 1,
                "nearest_park_miles": 0.5,
                "total_green_acres_1mi": 100.0,
                "greenspace_z_score": 0.5,
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
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["features"][0]["name"] == "Cached Park"
        # DB should not have been queried
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        """When cache misses, should query DB and write to cache."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None  # Cache miss

        mock_park_result = MagicMock()
        mock_park_result.all.return_value = [
            _make_park_row(feature_id="1", name="A Park", distance_miles=0.5, acreage=10.0),
        ]
        mock_greenway_result = MagicMock()
        mock_greenway_result.all.return_value = []

        mock_session.execute.side_effect = [mock_park_result, mock_greenway_result]

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        # DB was queried (parks + greenways = 2 calls)
        assert mock_session.execute.call_count == 2
        # Cache was written
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestGreenspaceHelperFunctions:
    """Tests for internal helper functions."""

    def test_cache_key_deterministic(self):
        """Same inputs should produce the same cache key."""
        from pricepoint.api.routes.greenspace import _cache_key

        k1 = _cache_key(35.79, -78.78, 2.0)
        k2 = _cache_key(35.79, -78.78, 2.0)
        assert k1 == k2

    def test_cache_key_varies_with_params(self):
        """Different inputs should produce different cache keys."""
        from pricepoint.api.routes.greenspace import _cache_key

        k1 = _cache_key(35.79, -78.78, 2.0)
        k2 = _cache_key(35.79, -78.78, 5.0)
        assert k1 != k2
