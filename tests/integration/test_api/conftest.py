"""API integration test fixtures with database override."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pricepoint.api.main import create_app
from pricepoint.db.engine import get_db


@pytest.fixture
def api_app(db_engine):
    """Create a FastAPI app with the DB dependency overridden to use testcontainer."""
    app = create_app()

    def _override_get_db():
        session = Session(bind=db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def api_client(api_app):
    """Test client wired to the testcontainer-backed app."""
    return TestClient(api_app)
