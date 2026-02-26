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


# --- Geometries endpoint tests ---


def _make_road_row(fullname="US-401"):
    return _FakeRow(
        geojson='{"type":"MultiLineString","coordinates":[[[-78.8,35.8],[-78.7,35.9]]]}',
        fullname=fullname,
    )


def _make_airport_row(name="RDU International", iata_code="RDU"):
    return _FakeRow(
        geojson='{"type":"Point","coordinates":[-78.79,35.88]}',
        name=name,
        iata_code=iata_code,
    )


def _make_railroad_row(rrowner1="CSX", subdivision="Raleigh"):
    return _FakeRow(
        geojson='{"type":"MultiLineString","coordinates":[[[-78.85,35.85],[-78.75,35.95]]]}',
        rrowner1=rrowner1,
        subdivision=subdivision,
    )


@pytest.fixture
def geom_app():
    """Create a test app with mocked DB returning geometry data for all layers."""
    app = create_app()
    mock_session = MagicMock()

    road_result = MagicMock()
    road_result.all.return_value = [_make_road_row()]

    airport_result = MagicMock()
    airport_result.all.return_value = [_make_airport_row()]

    railroad_result = MagicMock()
    railroad_result.all.return_value = [_make_railroad_row()]

    mock_session.execute.side_effect = [road_result, airport_result, railroad_result]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def geom_client(geom_app):
    return TestClient(geom_app)


@pytest.fixture
def empty_geom_app():
    """Create a test app with mocked DB returning no geometry data."""
    app = create_app()
    mock_session = MagicMock()

    empty_result = MagicMock()
    empty_result.all.return_value = []
    mock_session.execute.return_value = empty_result

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_geom_client(empty_geom_app):
    return TestClient(empty_geom_app)


class TestGeometriesReturns200:
    def test_returns_200_with_valid_params(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_feature_collection(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data


class TestGeometriesResponseShape:
    def test_returns_all_three_layers(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        layers = {f["properties"]["layer"] for f in features}
        assert layers == {"road", "airport", "railroad"}

    def test_returns_correct_feature_count(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["features"]) == 3

    def test_airport_feature_is_point_geometry(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        airport = next(f for f in features if f["properties"]["layer"] == "airport")
        assert airport["geometry"]["type"] == "Point"
        assert airport["properties"]["name"] == "RDU International"
        assert airport["properties"]["iata_code"] == "RDU"

    def test_road_feature_is_multilinestring(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        road = next(f for f in features if f["properties"]["layer"] == "road")
        assert road["geometry"]["type"] == "MultiLineString"
        assert road["properties"]["fullname"] == "US-401"

    def test_railroad_feature_is_multilinestring(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        rail = next(f for f in features if f["properties"]["layer"] == "railroad")
        assert rail["geometry"]["type"] == "MultiLineString"
        assert rail["properties"]["rrowner1"] == "CSX"
        assert rail["properties"]["subdivision"] == "Raleigh"


class TestGeometriesEmpty:
    def test_empty_returns_200(self, empty_geom_client):
        resp = empty_geom_client.get(
            "/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.status_code == 200

    def test_empty_features(self, empty_geom_client):
        resp = empty_geom_client.get(
            "/api/nuisances/geometries", params={"lat": 35.79, "lon": -78.78}
        )
        data = resp.json()
        assert data["type"] == "FeatureCollection"
        assert data["features"] == []


class TestGeometriesParamValidation:
    def test_missing_lat_returns_422(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, geom_client):
        resp = geom_client.get("/api/nuisances/geometries", params={"lat": 35.79})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, geom_client):
        resp = geom_client.get(
            "/api/nuisances/geometries",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422
