"""Integration tests to verify database schema creation."""

from sqlalchemy import inspect


def test_all_orm_tables_exist(db_engine):
    """All ORM-defined tables should be created in the database."""
    inspector = inspect(db_engine)
    tables = inspector.get_table_names()
    assert "properties" in tables
    assert "police_incidents" in tables
    assert "schools" in tables
    assert "staging_cary_police_incidents" in tables


def test_properties_has_location_column(db_engine):
    """The properties table should have a geometry location column."""
    inspector = inspect(db_engine)
    columns = {c["name"] for c in inspector.get_columns("properties")}
    assert "location" in columns


def test_parcel_id_index_exists(db_engine):
    """The properties table should have an index on parcel_id."""
    inspector = inspect(db_engine)
    indexes = inspector.get_indexes("properties")
    indexed_columns = {col for idx in indexes for col in idx["column_names"]}
    assert "parcel_id" in indexed_columns
