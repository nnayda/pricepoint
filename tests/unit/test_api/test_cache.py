"""Tests for the unified caching utilities and cache management endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.cache import async_cache_get, async_cache_set, cache_key, invalidate_pattern

# ---------------------------------------------------------------------------
# cache_key tests
# ---------------------------------------------------------------------------


class TestCacheKey:
    """Tests for the deterministic cache_key builder."""

    def test_determinism_same_params(self):
        """Identical prefix and params always produce the same key."""
        k1 = cache_key("crime", lat=35.7796, lon=-78.6382, radius=1.0)
        k2 = cache_key("crime", lat=35.7796, lon=-78.6382, radius=1.0)
        assert k1 == k2

    def test_determinism_param_order_independent(self):
        """Parameter ordering does not affect the resulting key."""
        k1 = cache_key("pois", lon=-78.6, lat=35.7)
        k2 = cache_key("pois", lat=35.7, lon=-78.6)
        assert k1 == k2

    def test_different_prefix_different_key(self):
        """Different prefixes produce different keys."""
        k1 = cache_key("crime", lat=35.7, lon=-78.6)
        k2 = cache_key("pois", lat=35.7, lon=-78.6)
        assert k1 != k2

    def test_key_starts_with_prefix(self):
        """Key always starts with 'prefix:'."""
        k = cache_key("geocode", q="raleigh")
        assert k.startswith("geocode:")


# ---------------------------------------------------------------------------
# async_cache_get / async_cache_set tests
# ---------------------------------------------------------------------------


class TestAsyncCacheGetSet:
    """Tests for get/set helpers."""

    @pytest.mark.asyncio
    async def test_get_returns_none_when_valkey_is_none(self):
        """When Valkey is not available, get returns None."""
        result = await async_cache_get(None, "any:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_when_key_missing(self):
        """When the key does not exist, get returns None."""
        mock_valkey = AsyncMock()
        mock_valkey.get.return_value = None
        result = await async_cache_get(mock_valkey, "missing:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(self):
        """Data stored via set is retrievable via get."""
        store: dict[str, str] = {}

        async def mock_set(key, value, ex=None):
            store[key] = value

        async def mock_get(key):
            return store.get(key)

        mock_valkey = AsyncMock()
        mock_valkey.set = mock_set
        mock_valkey.get = mock_get

        data = {"total": 42, "items": ["a", "b"]}
        await async_cache_set(mock_valkey, "test:roundtrip", data, ttl=300)
        result = await async_cache_get(mock_valkey, "test:roundtrip")
        assert result == data

    @pytest.mark.asyncio
    async def test_set_noop_when_valkey_is_none(self):
        """Set is a no-op when Valkey is None (no exception raised)."""
        await async_cache_set(None, "any:key", {"foo": 1}, ttl=60)

    @pytest.mark.asyncio
    async def test_get_handles_exception_gracefully(self):
        """If Valkey raises an error, get returns None instead of propagating."""
        mock_valkey = AsyncMock()
        mock_valkey.get.side_effect = ConnectionError("down")
        result = await async_cache_get(mock_valkey, "bad:key")
        assert result is None


# ---------------------------------------------------------------------------
# invalidate_pattern tests
# ---------------------------------------------------------------------------


class TestInvalidatePattern:
    """Tests for pattern-based key invalidation."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_valkey_is_none(self):
        """No-op when Valkey is unavailable."""
        deleted = await invalidate_pattern(None, "crime:*")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_deletes_matching_keys(self):
        """Matching keys are deleted and count is returned."""
        mock_valkey = AsyncMock()
        # scan returns (cursor, keys) — cursor 0 means done
        mock_valkey.scan.return_value = (0, ["crime:abc", "crime:def"])
        mock_valkey.delete.return_value = 2

        deleted = await invalidate_pattern(mock_valkey, "crime:*")
        assert deleted == 2
        mock_valkey.delete.assert_called_once_with("crime:abc", "crime:def")


# ---------------------------------------------------------------------------
# Cache management endpoint tests
# ---------------------------------------------------------------------------


class TestCacheManagementEndpoint:
    """Tests for DELETE /api/cache/{prefix}."""

    @pytest.fixture
    def client(self, app):
        """Create a TestClient with mocked auth."""
        return TestClient(app)

    def test_requires_auth(self, client):
        """Request without auth token returns 401."""
        resp = client.delete("/api/cache/crime")
        assert resp.status_code == 401

    def test_authenticated_invalidation(self, app):
        """Authenticated request returns deleted count."""
        from pricepoint.api.auth import get_current_user
        from pricepoint.api.dependencies import get_valkey

        mock_user = MagicMock()
        mock_user.is_active = True

        mock_valkey = AsyncMock()
        mock_valkey.scan.return_value = (0, ["crime:aaa"])
        mock_valkey.delete.return_value = 1

        app.dependency_overrides[get_current_user] = lambda: mock_user

        async def _override_valkey():
            yield mock_valkey

        app.dependency_overrides[get_valkey] = _override_valkey

        client = TestClient(app)
        resp = client.delete("/api/cache/crime")
        assert resp.status_code == 200
        body = resp.json()
        assert body["prefix"] == "crime"
        assert body["deleted"] == 1

        app.dependency_overrides.clear()

    def test_unknown_prefix_returns_error(self, app):
        """Unknown prefix returns an error message with zero deleted."""
        from pricepoint.api.auth import get_current_user

        mock_user = MagicMock()
        mock_user.is_active = True
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)
        resp = client.delete("/api/cache/badprefix")
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] == 0
        assert "error" in body

        app.dependency_overrides.clear()
