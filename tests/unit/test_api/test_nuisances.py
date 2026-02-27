"""Tests for the nuisances sources endpoint."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.dependencies import get_db
from pricepoint.api.main import create_app


class _FakeRow:
    """Lightweight row object that supports attribute access."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


def _make_noise_group_row(source_layer="aviation", max_db=65, noise_band="65-70 dB"):
    return _FakeRow(source_layer=source_layer, max_db=max_db, noise_band=noise_band)


def _make_airport_row(
    name="RDU International", iata_code="RDU", lat=35.88, lon=-78.79, dist_m=5000
):
    return _FakeRow(name=name, iata_code=iata_code, lat=lat, lon=lon, dist_m=dist_m)


def _make_road_row(fullname="US-401", lat=35.57, lon=-78.78, dist_m=500):
    return _FakeRow(fullname=fullname, lat=lat, lon=lon, dist_m=dist_m)


@pytest.fixture
def sources_app():
    """Create a test app with mocked DB returning nuisance source data."""
    app = create_app()
    mock_session = MagicMock()

    # Execute order:
    # 1. PropertyGeoLookup noise zone check → not found (None)
    # 2. Noise group query → 2 source layers
    # 3. Aviation nearest airport
    # 4. Road nearest road
    lookup_result = MagicMock()
    lookup_result.scalar_one_or_none.return_value = None

    noise_result = MagicMock()
    noise_result.all.return_value = [
        _make_noise_group_row(source_layer="aviation", max_db=65, noise_band="65-70 dB"),
        _make_noise_group_row(source_layer="road", max_db=50, noise_band="50-55 dB"),
    ]

    airport_result = MagicMock()
    airport_result.first.return_value = _make_airport_row()

    road_result = MagicMock()
    road_result.first.return_value = _make_road_row()

    mock_session.execute.side_effect = [
        lookup_result,
        noise_result,
        airport_result,
        road_result,
    ]

    def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def sources_client(sources_app):
    return TestClient(sources_app)


@pytest.fixture
def empty_sources_app():
    """Create a test app with mocked DB returning no noise data."""
    app = create_app()
    mock_session = MagicMock()

    lookup_result = MagicMock()
    lookup_result.scalar_one_or_none.return_value = None

    noise_result = MagicMock()
    noise_result.all.return_value = []

    mock_session.execute.side_effect = [lookup_result, noise_result]

    def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_sources_client(empty_sources_app):
    return TestClient(empty_sources_app)


class TestSourcesReturns200:
    def test_returns_200_with_valid_params(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)
        assert "sources" in data


class TestSourcesResponseShape:
    def test_sources_is_list(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["sources"], list)

    def test_returns_correct_count(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        assert len(resp.json()["sources"]) == 2

    def test_source_has_required_fields(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        sources = resp.json()["sources"]
        assert len(sources) > 0
        required = ["id", "name", "source_type", "severity", "distance_miles", "lat", "lon"]
        for field in required:
            assert field in sources[0], f"Missing field: {field}"


class TestSourcesSeverity:
    def test_high_db_maps_to_concern(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        sources = resp.json()["sources"]
        aviation = [s for s in sources if s["source_type"] == "aviation"]
        assert len(aviation) == 1
        assert aviation[0]["severity"] == "Concern"

    def test_low_db_maps_to_caution(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78})
        sources = resp.json()["sources"]
        road = [s for s in sources if s["source_type"] == "road"]
        assert len(road) == 1
        assert road[0]["severity"] == "Caution"


class TestSourcesEmpty:
    def test_empty_returns_200(self, empty_sources_client):
        resp = empty_sources_client.get(
            "/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.status_code == 200

    def test_empty_sources_list(self, empty_sources_client):
        resp = empty_sources_client.get(
            "/api/nuisances/sources", params={"lat": 35.79, "lon": -78.78}
        )
        assert resp.json()["sources"] == []


class TestSourcesParamValidation:
    def test_missing_lat_returns_422(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources", params={"lat": 35.79})
        assert resp.status_code == 422

    def test_missing_all_params_returns_422(self, sources_client):
        resp = sources_client.get("/api/nuisances/sources")
        assert resp.status_code == 422
