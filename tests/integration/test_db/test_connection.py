"""Integration tests for database connectivity.

These tests require a running PostGIS database. They are skipped
when DATABASE_URL is not reachable.
"""

import pytest
from sqlalchemy import text

from home_value_forecast.config.settings import Settings


@pytest.fixture
def db_engine():
    """Create a test database engine, skipping if unavailable."""
    from sqlalchemy import create_engine

    settings = Settings(_env_file=None)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Database not available")
    return engine


def test_database_connection(db_engine):
    """Verify we can connect to the database and run a query."""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS n"))
        assert result.scalar() == 1


def test_postgis_extension(db_engine):
    """Verify PostGIS extension is available."""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT PostGIS_Version()"))
        version = result.scalar()
        assert version is not None
