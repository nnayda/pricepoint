"""Tests for the risks endpoint."""

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


def _make_infra_row(
    infra_id="1",
    name="Test Feature",
    infrastructure_type="cell_tower",
    lat=35.79,
    lon=-78.78,
    distance_miles=0.5,
    rb_severity=None,
):
    return _FakeRow(
        infra_id=infra_id,
        name=name,
        infrastructure_type=infrastructure_type,
        lat=lat,
        lon=lon,
        distance_miles=distance_miles,
        rb_severity=rb_severity,
    )


def _make_boundary_row(
    geojson='{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}',
    infrastructure_type="power_plant",
    infrastructure_id=30,
    severity="critical",
):
    return _FakeRow(
        geojson=geojson,
        infrastructure_type=infrastructure_type,
        infrastructure_id=infrastructure_id,
        severity=severity,
    )


@pytest.fixture
def risks_app():
    """Create a test app with mocked DB returning risk features and boundaries."""
    app = create_app()
    mock_session = MagicMock()

    infra_rows = [
        _make_infra_row(
            infra_id="10",
            name="AT&T Tower",
            infrastructure_type="cell_tower",
            lat=35.80,
            lon=-78.77,
            distance_miles=0.8,
            rb_severity=None,
        ),
        _make_infra_row(
            infra_id="20",
            name="Duke Energy Line",
            infrastructure_type="transmission_line",
            lat=35.791,
            lon=-78.781,
            distance_miles=0.3,
            rb_severity="caution",
        ),
        _make_infra_row(
            infra_id="30",
            name="Shearon Harris",
            infrastructure_type="power_plant",
            lat=35.785,
            lon=-78.769,
            distance_miles=1.2,
            rb_severity="critical",
        ),
    ]

    boundary_rows = [
        _make_boundary_row(
            infrastructure_type="power_plant",
            infrastructure_id=30,
            severity="critical",
        ),
        _make_boundary_row(
            infrastructure_type="transmission_line",
            infrastructure_id=20,
            severity="caution",
        ),
    ]

    # First execute call returns infra rows, second returns boundary rows
    mock_result_infra = MagicMock()
    mock_result_infra.all.return_value = infra_rows
    mock_result_boundary = MagicMock()
    mock_result_boundary.all.return_value = boundary_rows
    mock_session.execute.side_effect = [mock_result_infra, mock_result_boundary]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def risks_client(risks_app):
    return TestClient(risks_app)


@pytest.fixture
def empty_risks_app():
    """Create a test app with mocked DB returning no features."""
    app = create_app()
    mock_session = MagicMock()

    mock_result_empty = MagicMock()
    mock_result_empty.all.return_value = []
    mock_session.execute.side_effect = [mock_result_empty, mock_result_empty]

    def _override_get_db():
        yield mock_session

    async def _override_get_valkey():
        yield None

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_valkey] = _override_get_valkey
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_risks_client(empty_risks_app):
    return TestClient(empty_risks_app)


class TestRisksReturns200:
    def test_returns_200_with_valid_params(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_response_is_json(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert isinstance(data, dict)


class TestRisksResponseShape:
    def test_response_has_features_and_boundary_geojson(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        data = resp.json()
        assert "features" in data
        assert "boundary_geojson" in data

    def test_features_is_list(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        assert isinstance(resp.json()["features"], list)

    def test_boundary_geojson_is_feature_collection(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        bg = resp.json()["boundary_geojson"]
        assert bg["type"] == "FeatureCollection"
        assert isinstance(bg["features"], list)


class TestRisksSeverityMapping:
    def test_critical_maps_to_concern(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        power_plant = [f for f in features if f["infrastructure_type"] == "power_plant"]
        assert len(power_plant) == 1
        assert power_plant[0]["severity"] == "Concern"

    def test_caution_maps_to_caution(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        tl = [f for f in features if f["infrastructure_type"] == "transmission_line"]
        assert len(tl) == 1
        assert tl[0]["severity"] == "Caution"

    def test_null_severity_maps_to_safe(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        ct = [f for f in features if f["infrastructure_type"] == "cell_tower"]
        assert len(ct) == 1
        assert ct[0]["severity"] == "Safe"


class TestRisksFeatureFields:
    def test_feature_has_required_fields(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        assert len(features) > 0
        for field in [
            "id",
            "name",
            "infrastructure_type",
            "severity",
            "distance_miles",
            "lat",
            "lon",
            "detail",
        ]:
            assert field in features[0], f"Missing field: {field}"

    def test_feature_id_has_prefix(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        ct = [f for f in features if f["infrastructure_type"] == "cell_tower"]
        assert ct[0]["id"].startswith("RB-C-")

    def test_detail_includes_zone_info(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        features = resp.json()["features"]
        pp = [f for f in features if f["infrastructure_type"] == "power_plant"]
        assert "critical risk zone" in pp[0]["detail"]


class TestRisksBoundaryGeoJSON:
    def test_boundary_features_have_properties(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        bg = resp.json()["boundary_geojson"]
        assert len(bg["features"]) == 2
        for f in bg["features"]:
            assert "properties" in f
            props = f["properties"]
            assert "infrastructure_type" in props
            assert "severity" in props

    def test_boundary_features_have_geometry(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        bg = resp.json()["boundary_geojson"]
        for f in bg["features"]:
            assert "geometry" in f
            assert f["geometry"]["type"] == "Polygon"


class TestRisksMissingParams:
    def test_missing_all_params_returns_422(self, risks_client):
        resp = risks_client.get("/api/risks")
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79})
        assert resp.status_code == 422


class TestRisksParamValidation:
    def test_lat_out_of_range_returns_422(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 91.0, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, risks_client):
        resp = risks_client.get("/api/risks", params={"lat": 35.79, "lon": 181.0})
        assert resp.status_code == 422

    def test_radius_zero_returns_422(self, risks_client):
        resp = risks_client.get(
            "/api/risks",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 0},
        )
        assert resp.status_code == 422

    def test_radius_too_large_returns_422(self, risks_client):
        resp = risks_client.get(
            "/api/risks",
            params={"lat": 35.79, "lon": -78.78, "radius_miles": 11},
        )
        assert resp.status_code == 422


class TestRisksEmptyResults:
    def test_empty_returns_200(self, empty_risks_client):
        resp = empty_risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200

    def test_empty_features_list(self, empty_risks_client):
        resp = empty_risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        assert resp.json()["features"] == []

    def test_empty_boundary_geojson(self, empty_risks_client):
        resp = empty_risks_client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        bg = resp.json()["boundary_geojson"]
        assert bg["type"] == "FeatureCollection"
        assert bg["features"] == []


class TestRisksValkeyCaching:
    def test_cache_hit_returns_cached_data(self):
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "features": [
                {
                    "id": "RB-C-1",
                    "name": "AT&T Tower",
                    "infrastructure_type": "cell_tower",
                    "severity": "Safe",
                    "distance_miles": 0.8,
                    "lat": 35.80,
                    "lon": -78.77,
                    "detail": "Cell Tower — outside risk zones",
                }
            ],
            "boundary_geojson": {"type": "FeatureCollection", "features": []},
        }
        mock_valkey.get.return_value = json.dumps(cached_response)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert resp.json()["features"][0]["name"] == "AT&T Tower"
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None

        infra_rows = [
            _make_infra_row(
                infra_id="10",
                name="AT&T Tower",
                infrastructure_type="cell_tower",
                distance_miles=0.8,
            ),
        ]
        mock_result_infra = MagicMock()
        mock_result_infra.all.return_value = infra_rows
        mock_result_boundary = MagicMock()
        mock_result_boundary.all.return_value = []
        mock_session.execute.side_effect = [mock_result_infra, mock_result_boundary]

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get("/api/risks", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        assert mock_session.execute.call_count == 2
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestRisksCacheKey:
    def test_cache_key_deterministic(self):
        from pricepoint.api.routes.risks import _cache_key

        k1 = _cache_key(35.79, -78.78, 3.0)
        k2 = _cache_key(35.79, -78.78, 3.0)
        assert k1 == k2

    def test_cache_key_varies_with_params(self):
        from pricepoint.api.routes.risks import _cache_key

        k1 = _cache_key(35.79, -78.78, 3.0)
        k2 = _cache_key(35.79, -78.78, 5.0)
        assert k1 != k2


class TestRisksSeverityHelpers:
    def test_severity_label_critical(self):
        from pricepoint.api.routes.risks import _severity_label

        assert _severity_label("critical") == "Concern"

    def test_severity_label_caution(self):
        from pricepoint.api.routes.risks import _severity_label

        assert _severity_label("caution") == "Caution"

    def test_severity_label_none(self):
        from pricepoint.api.routes.risks import _severity_label

        assert _severity_label(None) == "Safe"

    def test_detail_text_with_severity(self):
        from pricepoint.api.routes.risks import _detail_text

        detail = _detail_text("power_plant", "critical")
        assert "Power Plant" in detail
        assert "critical risk zone" in detail

    def test_detail_text_without_severity(self):
        from pricepoint.api.routes.risks import _detail_text

        detail = _detail_text("cell_tower", None)
        assert "Cell Tower" in detail
        assert "outside risk zones" in detail
