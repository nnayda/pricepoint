"""Integration tests for database connectivity using testcontainers."""

from sqlalchemy import text


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
