"""Tests for the utilities endpoint with real PostGIS query mocking."""

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


def _make_row(
    feature_id="1",
    name="Test Feature",
    feature_type="highway",
    lat=35.79,
    lon=-78.78,
    distance_miles=0.5,
):
    """Create a mock DB row for utilities query results."""
    return _FakeRow(
        feature_id=feature_id,
        name=name,
        feature_type=feature_type,
        lat=lat,
        lon=lon,
        distance_miles=distance_miles,
    )


@pytest.fixture
def utilities_app():
    """Create a test app with mocked DB that returns utility features."""
    app = create_app()
    mock_session = MagicMock()

    rows = [
        _make_row(
            feature_id="10",
            name="I-40",
            feature_type="highway",
            lat=35.80,
            lon=-78.77,
            distance_miles=0.8,
        ),
        _make_row(
            feature_id="20",
            name="Cary Pkwy",
            feature_type="road",
            lat=35.791,
            lon=-78.781,
            distance_miles=0.3,
        ),
        _make_row(
            feature_id="30",
            name="CSX Transportation",
            feature_type="railroad",
            lat=35.785,
            lon=-78.769,
            distance_miles=1.2,
        ),
        _make_row(
            feature_id="40",
            name="UTIL",
            feature_type="utility_easement",
            lat=35.792,
            lon=-78.772,
            distance_miles=0.6,
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
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def utilities_client(utilities_app):
    """Test client for the utilities app."""
    return TestClient(utilities_app)


@pytest.fixture
def empty_utilities_app():
    """Create a test app with mocked DB that returns no utility features."""
    app = create_app()
    mock_session = MagicMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_utilities_client(empty_utilities_app):
    """Test client for empty utilities results."""
    return TestClient(empty_utilities_app)


class TestUtilitiesReturns200:
    def test_returns_200_with_valid_params(self, utilities_client):
        """GET /api/utilities with valid params returns 200."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestUtilitiesResponseShape:
    def test_response_has_features_and_metrics(self, utilities_client):
        """Response contains 'features' and 'metrics' keys."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert "features" in data
        assert "metrics" in data

    def test_features_is_list(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["features"], list)

    def test_metrics_is_dict(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"], dict)


class TestUtilitiesDataTypes:
    def test_feature_has_required_fields(self, utilities_client):
        """Each feature has id, name, feature_type, lat, lon, distance_miles."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        assert len(features) > 0
        for field in ["id", "name", "feature_type", "lat", "lon", "distance_miles"]:
            assert field in features[0], f"Missing feature field: {field}"

    def test_feature_id_is_string(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["id"], str)

    def test_feature_name_is_string(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["name"], str)

    def test_feature_type_is_string(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["feature_type"], str)

    def test_distance_is_number(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        feature = resp.json()["features"][0]
        assert isinstance(feature["distance_miles"], (int, float))

    def test_metrics_has_required_fields(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        for field in [
            "nearest_highway_miles",
            "nearest_railroad_miles",
            "nearest_powerline_miles",
            "nuisance_score",
        ]:
            assert field in metrics, f"Missing metrics field: {field}"

    def test_nuisance_score_is_number(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["nuisance_score"], (int, float))

    def test_nearest_highway_is_number(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["metrics"]["nearest_highway_miles"], (int, float))


class TestUtilitiesMissingParams:
    def test_missing_all_params_returns_422(self, utilities_client):
        resp = utilities_client.get("/api/utilities")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79})
        assert resp.status_code == 422


class TestUtilitiesParamValidation:
    def test_lat_out_of_range_returns_422(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, utilities_client):
        resp = utilities_client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, utilities_client):
        resp = utilities_client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, utilities_client):
        resp = utilities_client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestUtilitiesDefaultRadius:
    def test_default_radius_works(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_explicit_radius_works(self, utilities_client):
        resp = utilities_client.get(
            "/api/utilities",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 5.0},
        )
        assert resp.status_code == 200


class TestUtilitiesWithData:
    """Tests that verify real data processing from mocked DB rows."""

    def test_feature_count_matches_rows(self, utilities_client):
        """Features list should match the number of mocked rows."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) == 4

    def test_features_have_varied_types(self, utilities_client):
        """Features should include different utility types."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        types = {f["feature_type"] for f in resp.json()["features"]}
        assert types == {"highway", "road", "railroad", "utility_easement"}

    def test_distances_are_positive(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        for feature in resp.json()["features"]:
            assert feature["distance_miles"] > 0

    def test_nearest_highway_uses_road_minimum(self, utilities_client):
        """nearest_highway_miles should be min of highway and road distances."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        # Road is 0.3, highway is 0.8, so nearest should be 0.3
        assert metrics["nearest_highway_miles"] == 0.3

    def test_nearest_railroad_distance(self, utilities_client):
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        assert metrics["nearest_railroad_miles"] == 1.2

    def test_nearest_powerline_distance(self, utilities_client):
        """nearest_powerline_miles maps to utility_easement type."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        metrics = resp.json()["metrics"]
        assert metrics["nearest_powerline_miles"] == 0.6

    def test_nuisance_score_in_range(self, utilities_client):
        """Nuisance score should be between 0 and 10."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        score = resp.json()["metrics"]["nuisance_score"]
        assert 0.0 <= score <= 10.0

    def test_feature_id_has_type_prefix(self, utilities_client):
        """Feature IDs should contain a type character prefix."""
        resp = utilities_client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        # Highway feature should have UT-H- prefix
        highway_features = [f for f in features if f["feature_type"] == "highway"]
        assert highway_features[0]["id"].startswith("UT-H-")


class TestUtilitiesEmptyResults:
    """Tests for when no infrastructure features are found."""

    def test_empty_returns_200(self, empty_utilities_client):
        resp = empty_utilities_client.get(
            "/api/utilities", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.status_code == 200

    def test_empty_features_list(self, empty_utilities_client):
        resp = empty_utilities_client.get(
            "/api/utilities", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.json()["features"] == []

    def test_empty_metrics_defaults_to_radius(self, empty_utilities_client):
        """When no features found, nearest distances default to radius_miles."""
        resp = empty_utilities_client.get(
            "/api/utilities", params={"lat": 35.79, "lon": -78.78}
        )
        metrics = resp.json()["metrics"]
        # Default radius is 3.0
        assert metrics["nearest_highway_miles"] == 3.0
        assert metrics["nearest_railroad_miles"] == 3.0
        assert metrics["nearest_powerline_miles"] == 3.0

    def test_empty_nuisance_score_zero(self, empty_utilities_client):
        """With all distances at radius (3 miles), nuisance score should be 0."""
        resp = empty_utilities_client.get(
            "/api/utilities", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.json()["metrics"]["nuisance_score"] == 0.0


class TestUtilitiesValkeyCaching:
    """Tests for Valkey cache integration."""

    def test_cache_hit_returns_cached_data(self):
        """When cache has data, should return it without DB query."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "features": [
                {
                    "id": "UT-H-1",
                    "name": "I-40",
                    "feature_type": "highway",
                    "lat": 35.80,
                    "lon": -78.77,
                    "distance_miles": 0.8,
                }
            ],
            "metrics": {
                "nearest_highway_miles": 0.8,
                "nearest_railroad_miles": 1.5,
                "nearest_powerline_miles": 0.6,
                "nuisance_score": 3.2,
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
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["features"][0]["name"] == "I-40"
        # DB should not have been queried
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        """When cache misses, should query DB and write to cache."""
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None  # Cache miss

        rows = [
            _make_row(
                feature_id="10",
                name="I-40",
                feature_type="highway",
                distance_miles=0.8,
            ),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_session.execute.return_value = mock_result

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/utilities", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        # DB was queried
        assert mock_session.execute.call_count == 1
        # Cache was written
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestUtilitiesNuisanceScore:
    """Tests for the nuisance score computation helper."""

    def test_all_zero_distance_max_score(self):
        """All infrastructure at distance 0 should yield maximum score 10."""
        from pricepoint.api.routes.utilities import _compute_nuisance_score

        score = _compute_nuisance_score(0.0, 0.0, 0.0)
        assert score == 10.0

    def test_all_far_away_zero_score(self):
        """All infrastructure at or beyond 3 miles should yield score 0."""
        from pricepoint.api.routes.utilities import _compute_nuisance_score

        score = _compute_nuisance_score(3.0, 3.0, 3.0)
        assert score == 0.0

    def test_railroad_has_highest_weight(self):
        """Railroad close (weight 3) should give higher score than highway close (weight 2)."""
        from pricepoint.api.routes.utilities import _compute_nuisance_score

        score_railroad_close = _compute_nuisance_score(0.5, 3.0, 3.0)
        score_highway_close = _compute_nuisance_score(3.0, 0.5, 3.0)
        assert score_railroad_close > score_highway_close

    def test_cache_key_deterministic(self):
        """Same inputs should produce the same cache key."""
        from pricepoint.api.routes.utilities import _cache_key

        k1 = _cache_key(35.79, -78.78, 3.0)
        k2 = _cache_key(35.79, -78.78, 3.0)
        assert k1 == k2

    def test_cache_key_varies_with_params(self):
        """Different inputs should produce different cache keys."""
        from pricepoint.api.routes.utilities import _cache_key

        k1 = _cache_key(35.79, -78.78, 3.0)
        k2 = _cache_key(35.79, -78.78, 5.0)
        assert k1 != k2
