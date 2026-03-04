"""Tests for saved-POI endpoints (autocomplete, CRUD, nearby)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.auth import get_current_user
from pricepoint.api.dependencies import get_db
from pricepoint.db.models import SavedPoi, User


@pytest.fixture
def fake_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(fake_user, mock_db):
    from pricepoint.config.settings import Settings, get_settings

    get_settings.cache_clear()
    test_settings = Settings(_env_file=None)  # type: ignore[call-arg]

    with (
        patch("pricepoint.config.settings.get_settings", return_value=test_settings),
        patch("pricepoint.api.rate_limit.get_settings", return_value=test_settings),
        patch("pricepoint.api.main.get_settings", return_value=test_settings),
        patch("pricepoint.api.auth.get_settings", return_value=test_settings),
    ):
        import pricepoint.api.rate_limit as rl_mod

        rl_mod.limiter = rl_mod.create_limiter()

        from pricepoint.api.main import create_app

        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with TestClient(app) as c:
            yield c

        app.dependency_overrides.clear()

    get_settings.cache_clear()


@pytest.fixture
def unauth_client(mock_db):
    """Client with no auth override — should get 401 on protected routes."""
    from pricepoint.config.settings import Settings, get_settings

    get_settings.cache_clear()
    test_settings = Settings(_env_file=None)  # type: ignore[call-arg]

    with (
        patch("pricepoint.config.settings.get_settings", return_value=test_settings),
        patch("pricepoint.api.rate_limit.get_settings", return_value=test_settings),
        patch("pricepoint.api.main.get_settings", return_value=test_settings),
        patch("pricepoint.api.auth.get_settings", return_value=test_settings),
    ):
        import pricepoint.api.rate_limit as rl_mod

        rl_mod.limiter = rl_mod.create_limiter()

        from pricepoint.api.main import create_app

        app = create_app()
        app.dependency_overrides[get_db] = lambda: mock_db

        with TestClient(app) as c:
            yield c

        app.dependency_overrides.clear()

    get_settings.cache_clear()


def _make_saved_poi(
    id: int = 1,
    user_id: int = 1,
    match_type: str = "brand",
    match_value: str = "Costco",
    display_name: str = "Costco",
    category: str | None = "store",
) -> MagicMock:
    sp = MagicMock(spec=SavedPoi)
    sp.id = id
    sp.user_id = user_id
    sp.match_type = match_type
    sp.match_value = match_value
    sp.display_name = display_name
    sp.category = category
    sp.created_at = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    return sp


# --- Autocomplete tests ---


class TestAutocomplete:
    def test_returns_brand_results(self, client, mock_db):
        # Mock brand query returning rows
        brand_row = MagicMock()
        brand_row.value = "Costco"
        brand_row.cnt = 47
        brand_row.category = "store"

        # First execute = brand query, second = name query
        mock_db.execute.side_effect = [
            MagicMock(all=MagicMock(return_value=[brand_row])),
            MagicMock(all=MagicMock(return_value=[])),
        ]

        resp = client.get("/api/pois/autocomplete", params={"q": "cost"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "cost"
        assert len(data["results"]) == 1
        assert data["results"][0]["match_type"] == "brand"
        assert data["results"][0]["match_value"] == "Costco"
        assert data["results"][0]["count"] == 47

    def test_rejects_short_query(self, client):
        resp = client.get("/api/pois/autocomplete", params={"q": "c"})
        assert resp.status_code == 422

    def test_returns_name_fallback(self, client, mock_db):
        name_row = MagicMock()
        name_row.value = "Joe's Pizza"
        name_row.cnt = 3
        name_row.category = "restaurant"

        mock_db.execute.side_effect = [
            MagicMock(all=MagicMock(return_value=[])),  # no brands
            MagicMock(all=MagicMock(return_value=[name_row])),  # name fallback
        ]

        resp = client.get("/api/pois/autocomplete", params={"q": "joe"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["match_type"] == "name"


# --- CRUD tests ---


class TestSavedPoiCrud:
    def test_list_saved_pois(self, client, mock_db):
        saved = _make_saved_poi()
        mock_db.execute.return_value.scalars.return_value.all.return_value = [saved]

        resp = client.get("/api/saved-pois")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Costco"
        assert data[0]["match_type"] == "brand"

    def test_create_saved_poi(self, client, mock_db):
        # First execute: check existence (returns a Place id)
        # Second execute: check duplicate (returns None)
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=42)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]

        def _refresh(obj):
            obj.id = 1
            obj.created_at = datetime(2025, 6, 1, tzinfo=UTC)

        mock_db.refresh = MagicMock(side_effect=_refresh)

        resp = client.post(
            "/api/saved-pois",
            json={
                "match_type": "brand",
                "match_value": "Costco",
                "display_name": "Costco",
                "category": "store",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["match_value"] == "Costco"

    def test_create_not_found_in_places(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = client.post(
            "/api/saved-pois",
            json={
                "match_type": "brand",
                "match_value": "NonExistent",
                "display_name": "NonExistent",
            },
        )
        assert resp.status_code == 404

    def test_create_duplicate_returns_409(self, client, mock_db):
        existing = _make_saved_poi()
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=42)),  # exists in places
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing)),  # duplicate
        ]

        resp = client.post(
            "/api/saved-pois",
            json={
                "match_type": "brand",
                "match_value": "Costco",
                "display_name": "Costco",
            },
        )
        assert resp.status_code == 409

    def test_delete_saved_poi(self, client, mock_db):
        saved = _make_saved_poi(user_id=1)
        mock_db.execute.return_value.scalar_one_or_none.return_value = saved

        resp = client.delete("/api/saved-pois/1")
        assert resp.status_code == 204
        mock_db.delete.assert_called_once_with(saved)

    def test_delete_not_found(self, client, mock_db):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        resp = client.delete("/api/saved-pois/999")
        assert resp.status_code == 404

    def test_delete_forbidden(self, client, mock_db):
        saved = _make_saved_poi(user_id=2)  # owned by another user
        mock_db.execute.return_value.scalar_one_or_none.return_value = saved

        resp = client.delete("/api/saved-pois/1")
        assert resp.status_code == 403

    def test_unauthenticated_list(self, unauth_client):
        resp = unauth_client.get("/api/saved-pois")
        assert resp.status_code == 401

    def test_unauthenticated_create(self, unauth_client):
        resp = unauth_client.post(
            "/api/saved-pois",
            json={
                "match_type": "brand",
                "match_value": "Costco",
                "display_name": "Costco",
            },
        )
        assert resp.status_code == 401


# --- Nearby tests ---


class TestSavedPoiNearby:
    def test_empty_when_no_saved(self, client, mock_db):
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        resp = client.get("/api/pois/saved-nearby", params={"lat": 35.7, "lon": -78.6})
        assert resp.status_code == 200
        assert resp.json()["groups"] == []

    def test_unauthenticated(self, unauth_client):
        resp = unauth_client.get("/api/pois/saved-nearby", params={"lat": 35.7, "lon": -78.6})
        assert resp.status_code == 401
