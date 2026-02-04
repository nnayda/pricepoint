"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from home_value_forecast.api.main import create_app


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test HTTP client."""
    return TestClient(app)
