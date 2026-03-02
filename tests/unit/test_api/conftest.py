"""Unit-level API test fixtures — mocks DB dependency for isolation."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.api.dependencies import get_db


@pytest.fixture
def app():
    """Create a test FastAPI application with mocked DB.

    Patches ``valkey_url`` to ``None`` so the rate limiter uses in-memory
    storage instead of trying to reach an external Valkey instance during
    unit tests.
    """
    from pricepoint.config.settings import Settings, get_settings

    # Clear cached settings singleton
    get_settings.cache_clear()

    # Build a settings object with valkey disabled (skip .env file)
    test_settings = Settings(_env_file=None)  # type: ignore[call-arg]

    # Patch get_settings everywhere it is imported
    with (
        patch("pricepoint.config.settings.get_settings", return_value=test_settings),
        patch("pricepoint.api.rate_limit.get_settings", return_value=test_settings),
        patch("pricepoint.api.main.get_settings", return_value=test_settings),
        patch("pricepoint.api.auth.get_settings", return_value=test_settings),
    ):
        # Re-create rate limiter with in-memory backend
        import pricepoint.api.rate_limit as rl_mod

        rl_mod.limiter = rl_mod.create_limiter()

        from pricepoint.api.main import create_app

        application = create_app()

        mock_session = MagicMock()
        # Default: queries return None (no DB records found) → stubs used
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        # Default: .query(...).filter(...).limit(...).all() returns [] (geocode DB search)
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []

        def _override_get_db():
            yield mock_session

        application.dependency_overrides[get_db] = _override_get_db
        yield application
        application.dependency_overrides.clear()

    # Restore original settings cache
    get_settings.cache_clear()
