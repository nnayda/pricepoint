"""Tests for the POI search endpoint (/api/pois/search)."""

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


def _make_search_row(
    poi_id="1",
    poi_name="Costco Wholesale",
    category="warehouse_club",
    brand_name="Costco",
    address="123 Main St",
    phone="+19195551234",
    lat=35.79,
    lon=-78.78,
    distance_miles=1.5,
):
    return _FakeRow(
        poi_id=poi_id,
        poi_name=poi_name,
        category=category,
        brand_name=brand_name,
        address=address,
        phone=phone,
        lat=lat,
        lon=lon,
        distance_miles=distance_miles,
    )


def _make_search_app(rows=None):
    """Create a test app with mocked DB returning the given search rows."""
    app = create_app()
    mock_session = MagicMock()

    if rows is None:
        rows = [
            _make_search_row(
                poi_id="1",
                poi_name="Costco Wholesale",
                category="warehouse_club",
                distance_miles=1.2,
            ),
            _make_search_row(
                poi_id="2",
                poi_name="Costco Gas",
                category="gas_station",
                distance_miles=1.3,
                lat=35.791,
                lon=-78.781,
            ),
            _make_search_row(
                poi_id="3",
                poi_name="Costco Pharmacy",
                category="pharmacy",
                distance_miles=1.4,
                lat=35.792,
                lon=-78.782,
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
def search_app():
    app, _ = _make_search_app()
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def search_client(search_app):
    return TestClient(search_app)


@pytest.fixture
def empty_search_app():
    app, _ = _make_search_app(rows=[])
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def empty_search_client(empty_search_app):
    return TestClient(empty_search_app)


class TestSearchReturns200:
    def test_returns_200_with_valid_params(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert resp.status_code == 200

    def test_response_is_json(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert isinstance(resp.json(), dict)


class TestSearchResponseShape:
    def test_response_has_pois_key(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert "pois" in resp.json()

    def test_response_has_total_count(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert "total_count" in resp.json()

    def test_response_has_query(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert resp.json()["query"] == "costco"

    def test_pois_is_list(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert isinstance(resp.json()["pois"], list)


class TestSearchDataTypes:
    def test_poi_has_required_fields(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        pois = resp.json()["pois"]
        assert len(pois) > 0
        for field in ["id", "name", "category", "lat", "lon", "distance_miles", "drive_minutes"]:
            assert field in pois[0], f"Missing field: {field}"

    def test_poi_id_has_overture_prefix(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        poi = resp.json()["pois"][0]
        assert poi["id"].startswith("OVERTURE-")


class TestSearchMissingParams:
    def test_missing_query_returns_422(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78},
        )
        assert resp.status_code == 422

    def test_missing_lat_returns_422(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lon": -78.78, "query": "costco"},
        )
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "query": "costco"},
        )
        assert resp.status_code == 422

    def test_empty_query_returns_422(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": ""},
        )
        assert resp.status_code == 422


class TestSearchWithData:
    def test_total_count_matches_pois(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        data = resp.json()
        assert data["total_count"] == len(data["pois"])

    def test_returns_3_results(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert len(resp.json()["pois"]) == 3

    def test_drive_minutes_at_least_1(self, search_client):
        resp = search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        for poi in resp.json()["pois"]:
            assert poi["drive_minutes"] >= 1


class TestSearchEmptyResults:
    def test_empty_returns_200(self, empty_search_client):
        resp = empty_search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "nonexistent"},
        )
        assert resp.status_code == 200

    def test_empty_pois_list(self, empty_search_client):
        resp = empty_search_client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "nonexistent"},
        )
        assert resp.json()["pois"] == []
        assert resp.json()["total_count"] == 0


class TestSearchValkeyCaching:
    def test_cache_hit_returns_cached_data(self):
        app = create_app()
        mock_session = MagicMock()
        mock_valkey = AsyncMock()

        cached_response = {
            "pois": [
                {
                    "id": "OVERTURE-1",
                    "name": "Cached Costco",
                    "category": "warehouse_club",
                    "lat": 35.79,
                    "lon": -78.78,
                    "distance_miles": 1.5,
                    "drive_minutes": 5,
                }
            ],
            "total_count": 1,
            "query": "costco",
        }
        mock_valkey.get.return_value = json.dumps(cached_response)

        def _override_get_db():
            yield mock_session

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert resp.status_code == 200
        assert resp.json()["pois"][0]["name"] == "Cached Costco"
        mock_session.execute.assert_not_called()
        app.dependency_overrides.clear()

    def test_cache_miss_queries_db_and_caches(self):
        app, mock_session = _make_search_app()
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None

        async def _override_get_valkey():
            yield mock_valkey

        app.dependency_overrides[get_valkey] = _override_get_valkey

        client = TestClient(app)
        resp = client.get(
            "/api/pois/search",
            params={"lat": 35.79, "lon": -78.78, "query": "costco"},
        )
        assert resp.status_code == 200
        assert mock_session.execute.call_count == 1
        mock_valkey.set.assert_called_once()
        app.dependency_overrides.clear()


class TestSearchCacheKey:
    def test_cache_key_deterministic(self):
        from pricepoint.api.routes.pois import _search_cache_key

        k1 = _search_cache_key(35.79, -78.78, "costco", 5.0)
        k2 = _search_cache_key(35.79, -78.78, "costco", 5.0)
        assert k1 == k2

    def test_cache_key_varies_with_query(self):
        from pricepoint.api.routes.pois import _search_cache_key

        k1 = _search_cache_key(35.79, -78.78, "costco", 5.0)
        k2 = _search_cache_key(35.79, -78.78, "walmart", 5.0)
        assert k1 != k2

    def test_cache_key_case_insensitive(self):
        from pricepoint.api.routes.pois import _search_cache_key

        k1 = _search_cache_key(35.79, -78.78, "Costco", 5.0)
        k2 = _search_cache_key(35.79, -78.78, "costco", 5.0)
        assert k1 == k2

    def test_cache_key_starts_with_prefix(self):
        from pricepoint.api.routes.pois import _search_cache_key

        k = _search_cache_key(35.79, -78.78, "costco", 5.0)
        assert k.startswith("poi-search:")
