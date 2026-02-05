"""Shared test fixtures and automatic marker application."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pricepoint.api.main import create_app
from pricepoint.config.settings import get_settings


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply markers based on test file path."""
    for item in items:
        test_path = str(Path(item.fspath).resolve())
        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/docker/" in test_path:
            item.add_marker(pytest.mark.docker)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the cached settings before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test HTTP client."""
    return TestClient(app)
