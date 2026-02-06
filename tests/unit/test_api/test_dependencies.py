"""Tests for FastAPI dependencies."""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from pricepoint.api.dependencies import get_valkey


@pytest.fixture
def _valkey_app():
    """Create a minimal FastAPI app that uses the get_valkey dependency."""
    app = FastAPI()

    @app.get("/test-valkey")
    async def _read(valkey: Redis | None = Depends(get_valkey)):  # noqa: B008
        return {"has_valkey": valkey is not None}

    return app


@pytest.mark.asyncio
class TestGetValkey:
    async def test_yields_none_when_pool_not_set(self, _valkey_app):
        """When app.state has no valkey_pool, get_valkey should yield None."""
        async with AsyncClient(
            transport=ASGITransport(app=_valkey_app), base_url="http://test"
        ) as client:
            resp = await client.get("/test-valkey")

        assert resp.status_code == 200
        assert resp.json() == {"has_valkey": False}

    async def test_yields_pool_when_set(self, _valkey_app):
        """When app.state.valkey_pool is set, get_valkey should yield it."""
        sentinel = object.__new__(Redis)
        _valkey_app.state.valkey_pool = sentinel

        async with AsyncClient(
            transport=ASGITransport(app=_valkey_app), base_url="http://test"
        ) as client:
            resp = await client.get("/test-valkey")

        assert resp.status_code == 200
        assert resp.json() == {"has_valkey": True}
