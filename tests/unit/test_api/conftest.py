"""Unit-level API test fixtures — mocks DB dependency for isolation."""

from unittest.mock import MagicMock

import pytest

from pricepoint.api.dependencies import get_db
from pricepoint.api.main import create_app


@pytest.fixture
def app():
    """Create a test FastAPI application with mocked DB."""
    application = create_app()

    mock_session = MagicMock()
    # Default: queries return None (no DB records found) → stubs used
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    def _override_get_db():
        yield mock_session

    application.dependency_overrides[get_db] = _override_get_db
    yield application
    application.dependency_overrides.clear()
