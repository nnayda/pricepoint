"""Tests for the nuisances noise endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db, get_valkey
from pricepoint.api.main import create_app


class _FakeRow:
    """Lightweight row object that supports attribute access."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


def _make_noise_row(
    geojson='{"type":"MultiPolygon","coordinates":[[[[0,0],[1,0],[1,1],[0,1],[0,0]]]]}',
    noise_band="55-60 dB",
    noise_min_db=55,
    noise_max_db=60,
    source_layer="road",
    area_sq_m=1234.5,
):
    return _FakeRow(
        geojson=geojson,
        noise_band=noise_band,
        noise_min_db=noise_min_db,
        noise_max_db=noise_max_db,
        source_layer=source_layer,
        area_sq_m=area_sq_m,
    )


@pytest.fixture
def noise_app():
    """Create a test app with mocked DB returning noise data."""
    app = create_app()
    mock_session = MagicMock()

    rows = [
        _make_noise_row(
            noise_band="45-50 dB",
            noise_min_db=45,
            noise_max_db=50,
            source_layer="aviation",
        ),
        _make_noise_row(
            noise_band="55-60 dB",
            noise_min_db=55,
            noise_max_db=60,
            source_layer="road",
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
def noise_client(noise_app):
    return TestClient(noise_app)


@pytest.fixture
def empty_noise_app():
    """Create a test app with mocked DB returning no noise data."""
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
def empty_noise_client(empty_noise_app):
    return TestClient(empty_noise_app)


class TestNoiseReturns200:
    def test_returns_200_with_valid_params(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestNoiseResponseShape:
    def test_response_is_feature_collection(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data

    def test_features_is_list(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["features"], list)

    def test_feature_has_geojson_structure(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        assert len(features) > 0
        f = features[0]
        assert f["type"] == "Feature"
        assert "geometry" in f
        assert "properties" in f

    def test_feature_properties_have_required_fields(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        props = resp.json()["features"][0]["properties"]
        for field in ["noise_band", "noise_min_db", "source_layer"]:
            assert field in props, f"Missing property field: {field}"


class TestNoiseWithData:
    def test_returns_correct_count(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) == 2

    def test_features_ordered_by_min_db(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        dbs = [f["properties"]["noise_min_db"] for f in resp.json()["features"]]
        assert dbs == sorted(dbs)

    def test_geometry_is_multipolygon(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        geom = resp.json()["features"][0]["geometry"]
        assert geom["type"] == "MultiPolygon"


class TestNoiseEmptyResults:
    def test_empty_returns_200(self, empty_noise_client):
        resp = empty_noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_empty_features(self, empty_noise_client):
        resp = empty_noise_client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert data["features"] == []


class TestNoiseParamValidation:
    def test_missing_lat_returns_422(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise", params={"lat": 35.79})
        assert resp.status_code == 422

    def test_missing_all_params_returns_422(self, noise_client):
        resp = noise_client.get("/api/nuisances/noise")
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, noise_client):
        resp = noise_client.get(
            "/api/nuisances/noise",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_negative_returns_422(self, noise_client):
        resp = noise_client.get(
            "/api/nuisances/noise",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": -1},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, noise_client):
        resp = noise_client.get(
            "/api/nuisances/noise",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestNoiseValkeyCaching:
    def test_cache_hit_returns_cached_data(self):
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]],
                    },
                    "properties": {
                        "noise_band": "45-50 dB",
                        "noise_min_db": 45,
                        "noise_max_db": 50,
                        "source_layer": "aviation",
                        "area_sq_m": 100.0,
                    },
                }
            ],
        }
        mock_valkey.get.return_value = json.dumps(cached_response)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["features"][0]["properties"]["noise_band"] == "45-50 dB"
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/nuisances/noise", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        mock_session.execute.assert_called_once()
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestNoiseCacheKey:
    def test_cache_key_deterministic(self):
        from pricepoint.api.routes.nuisances import _cache_key

        k1 = _cache_key(35.79, -78.78, 2.0)
        k2 = _cache_key(35.79, -78.78, 2.0)
        assert k1 == k2

    def test_cache_key_varies_with_params(self):
        from pricepoint.api.routes.nuisances import _cache_key

        k1 = _cache_key(35.79, -78.78, 2.0)
        k2 = _cache_key(35.79, -78.78, 5.0)
        assert k1 != k2
