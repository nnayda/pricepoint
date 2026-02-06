"""Tests for application lifespan (Valkey pool init/close)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from pricepoint.api.main import lifespan
from pricepoint.config.settings import Settings


def _settings(**overrides) -> Settings:
    """Build a Settings instance ignoring .env files."""
    return Settings(**{"valkey_url": None, **overrides}, _env_file=None)


@pytest.mark.asyncio
class TestLifespanValkey:
    async def test_pool_initialised_when_url_configured(self):
        """When VALKEY_URL is set, lifespan should create a pool on app.state."""
        app = FastAPI()
        mock_pool = AsyncMock()

        with (
            patch(
                "pricepoint.api.main.get_settings",
                return_value=_settings(valkey_url="redis://localhost:6379/0"),
            ),
            patch("pricepoint.api.main.Redis.from_url", return_value=mock_pool),
        ):
            async with lifespan(app):
                assert app.state.valkey_pool is mock_pool

    async def test_pool_none_when_url_not_configured(self):
        """When VALKEY_URL is not set, valkey_pool should be None."""
        app = FastAPI()

        with patch(
            "pricepoint.api.main.get_settings",
            return_value=_settings(valkey_url=None),
        ):
            async with lifespan(app):
                assert app.state.valkey_pool is None

    async def test_pool_closed_on_shutdown(self):
        """The Valkey pool should be closed during application shutdown."""
        app = FastAPI()
        mock_pool = AsyncMock()

        with (
            patch(
                "pricepoint.api.main.get_settings",
                return_value=_settings(valkey_url="redis://localhost:6379/0"),
            ),
            patch("pricepoint.api.main.Redis.from_url", return_value=mock_pool),
        ):
            async with lifespan(app):
                mock_pool.aclose.assert_not_awaited()

            mock_pool.aclose.assert_awaited_once()

    async def test_aclose_not_called_when_no_pool(self):
        """When no pool is configured, shutdown should not attempt to close."""
        app = FastAPI()

        with patch(
            "pricepoint.api.main.get_settings",
            return_value=_settings(valkey_url=None),
        ):
            async with lifespan(app):
                assert app.state.valkey_pool is None
