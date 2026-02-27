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


def _make_park_row(
    feature_id="1",
    name="Test Park",
    feature_type="park",
    lat=35.79,
    lon=-78.78,
    distance_miles=0.5,
    acreage=12.5,
    source="padus",
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


def _mock_session_with(park_rows=None, greenway_rows=None, bg_row=None, metric_row=None):
    """Create a mock session that returns park, greenway, block group, and metric rows."""
    mock_session = MagicMock()

    mock_park_result = MagicMock()
    mock_park_result.all.return_value = park_rows or []

    mock_greenway_result = MagicMock()
    mock_greenway_result.all.return_value = greenway_rows or []

    # Block group lookup returns .first()
    mock_bg_result = MagicMock()
    mock_bg_result.first.return_value = bg_row

    # Metric lookup returns .first()
    mock_metric_result = MagicMock()
    mock_metric_result.first.return_value = metric_row

    mock_session.execute.side_effect = [
        mock_park_result,
        mock_greenway_result,
        mock_bg_result,
        mock_metric_result,
    ]
    return mock_session


@pytest.fixture
def greenspace_app():
    """Create a test app with mocked DB returning park and greenway data."""
    app = create_app()

    park_rows = [
        _make_park_row(
            feature_id="10",
            name="Umstead State Park",
            distance_miles=0.5,
            acreage=55.3,
        ),
        _make_park_row(
            feature_id="20",
            name="Lake Johnson Park",
            distance_miles=1.5,
            acreage=28.0,
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

    mock_session = _mock_session_with(park_rows, greenway_rows, bg_row=None, metric_row=None)

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
    mock_session = _mock_session_with([], [], bg_row=None, metric_row=None)

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
            "nearest_greenway_miles",
            "total_green_acres_1mi",
            "greenspace_z_score",
        ]:
            assert field in metrics, f"Missing metric field: {field}"


class TestGreenspaceWithData:
    """Tests that verify real data processing from mocked DB rows."""

    def test_total_features_count(self, greenspace_client):
        """Should return 4 features (2 parks + 2 trails)."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) == 4

    def test_trail_features_have_no_acreage(self, greenspace_client):
        """Trail features should have null acreage."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        trails = [f for f in resp.json()["features"] if f["feature_type"] == "trail"]
        assert len(trails) == 2
        for trail in trails:
            assert trail["acreage"] is None

    def test_park_features_have_acreage(self, greenspace_client):
        """Park features should have acreage set."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        parks = [f for f in resp.json()["features"] if f["feature_type"] == "park"]
        assert len(parks) == 2
        assert parks[0]["acreage"] == 55.3

    def test_parks_within_1mi_metric(self, greenspace_client):
        """Should count parks within 1 mile (Umstead at 0.5mi)."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["parks_within_1mi"] == 1

    def test_nearest_park_miles(self, greenspace_client):
        """Nearest park should be Umstead at 0.5mi."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["nearest_park_miles"] == 0.5

    def test_nearest_greenway_miles(self, greenspace_client):
        """Nearest greenway should be Black Creek at 0.3mi."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["nearest_greenway_miles"] == 0.3

    def test_total_green_acres_1mi(self, greenspace_client):
        """Green acres within 1mi should only count Umstead (55.3)."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["total_green_acres_1mi"] == 55.3

    def test_greenspace_z_score_zero(self, greenspace_client):
        """Z-score defaults to 0.0."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["metrics"]["greenspace_z_score"] == 0.0

    def test_features_sorted_by_distance(self, greenspace_client):
        """Features should be sorted by distance ascending."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        distances = [f["distance_miles"] for f in resp.json()["features"]]
        assert distances == sorted(distances)

    def test_feature_ids_include_source(self, greenspace_client):
        """Feature IDs should include type and source prefix."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        ids = [f["id"] for f in resp.json()["features"]]
        assert any("trail-wake-" in i for i in ids)
        assert any("trail-raleigh-" in i for i in ids)
        assert any("park-padus-" in i for i in ids)

    def test_park_feature_type_is_park(self, greenspace_client):
        """Park features should have feature_type 'park'."""
        resp = greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        parks = [f for f in resp.json()["features"] if f["feature_type"] == "park"]
        assert len(parks) == 2


class TestGreenspaceZScoreLookup:
    """Tests for greenspace z-score lookup from precomputed metrics."""

    def test_returns_precomputed_zscore(self):
        """When block group and metric row exist, should return the z-score."""
        app = create_app()

        park_rows = [_make_park_row(distance_miles=0.5, acreage=10.0)]
        greenway_rows = [_make_greenway_row(distance_miles=0.3)]

        bg_row = _FakeRow(geoid="371830501001")
        metric_row = _FakeRow(greenspace_ratio_zscore=1.45)

        mock_session = _mock_session_with(park_rows, greenway_rows, bg_row, metric_row)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield None

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["metrics"]["greenspace_z_score"] == 1.45
        app.dependency_overrides.clear()

    def test_falls_back_to_zero_when_no_block_group(self):
        """When no block group contains the point, z-score should be 0.0."""
        app = create_app()

        mock_session = _mock_session_with([], [], bg_row=None, metric_row=None)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield None

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["metrics"]["greenspace_z_score"] == 0.0
        app.dependency_overrides.clear()


class TestGreenspaceEmptyResults:
    """Tests for when no greenspace features are found."""

    def test_empty_returns_200(self, empty_greenspace_client):
        """Should still return 200 with empty lists."""
        resp = empty_greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_empty_features(self, empty_greenspace_client):
        resp = empty_greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["features"] == []

    def test_empty_metrics_zeros(self, empty_greenspace_client):
        resp = empty_greenspace_client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        assert metrics["parks_within_1mi"] == 0
        assert metrics["nearest_park_miles"] == 0.0
        assert metrics["nearest_greenway_miles"] == 0.0
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
                    "id": "trail-wake-1",
                    "name": "Cached Trail",
                    "feature_type": "trail",
                    "lat": 35.79,
                    "lon": -78.78,
                    "distance_miles": 0.5,
                    "acreage": None,
                }
            ],
            "metrics": {
                "parks_within_1mi": 0,
                "nearest_park_miles": 0.0,
                "nearest_greenway_miles": 0.0,
                "total_green_acres_1mi": 0.0,
                "greenspace_z_score": 0.0,
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
        assert resp.json()["features"][0]["name"] == "Cached Trail"
        # DB should not have been queried
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        """When cache misses, should query DB and write to cache."""
        app = create_app()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None  # Cache miss

        mock_session = _mock_session_with([], [], bg_row=None, metric_row=None)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/greenspace", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        # DB was queried (parks + greenways + block group lookup = 3 calls min)
        assert mock_session.execute.call_count >= 2
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
