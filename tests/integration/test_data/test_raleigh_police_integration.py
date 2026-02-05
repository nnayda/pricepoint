"""Integration tests for Raleigh police incidents collector against a real PostGIS database."""

from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text

from pricepoint.data.geospatial.police_incidents import fetch_raleigh_police_incidents
from pricepoint.db.models import StagingRaleighPoliceIncident

pytestmark = pytest.mark.integration


def _make_feature(**overrides: object) -> dict:
    """Return a minimal ArcGIS feature dict with optional attribute overrides."""
    attrs: dict[str, object] = {
        "OBJECTID": 1,
        "GlobalID": "abc-123",
        "case_number": "24-001001",
        "crime_category": "LARCENY",
        "crime_code": "23F",
        "crime_description": "THEFT FROM MOTOR VEHICLE",
        "crime_type": "PROPERTY",
        "reported_block_address": "100 FAYETTEVILLE ST",
        "city_of_incident": "RALEIGH",
        "city": "RALEIGH",
        "district": "DOWNTOWN",
        "reported_date": 1705312800000,
        "reported_year": 2024,
        "reported_month": 1,
        "reported_day": 15,
        "reported_hour": 10,
        "reported_dayofwk": "MONDAY",
        "latitude": 35.780,
        "longitude": -78.639,
        "agency": "RPD",
        "updated_date": 1705399200000,
    }
    attrs.update(overrides)
    return {"attributes": attrs}


@patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_records_persist_to_staging_table(mock_session_cls, mock_query, db_session):
    """Records should be persisted to the staging table with correct field values."""
    mock_session_cls.return_value = db_session

    mock_query.return_value = [
        _make_feature(case_number="INT-R1", crime_category="ASSAULT"),
    ]

    fetch_raleigh_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingRaleighPoliceIncident)).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.case_number == "INT-R1"
    assert row.crime_category == "ASSAULT"
    assert row.district == "DOWNTOWN"
    assert row.latitude == pytest.approx(35.780)
    assert row.longitude == pytest.approx(-78.639)
    assert row.location is not None


@patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_full_refresh_truncates_before_load(mock_session_cls, mock_query, db_session):
    """Full refresh should remove old records and only keep new ones."""
    mock_session_cls.return_value = db_session

    # Seed an old record
    old = StagingRaleighPoliceIncident(case_number="OLD-001", crime_category="OLD")
    db_session.add(old)
    db_session.flush()

    # Mock returns a different record
    mock_query.return_value = [_make_feature(case_number="NEW-001")]

    fetch_raleigh_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingRaleighPoliceIncident)).scalars().all()
    case_numbers = {r.case_number for r in rows}
    assert "OLD-001" not in case_numbers
    assert "NEW-001" in case_numbers
    assert len(rows) == 1


@patch("pricepoint.data.geospatial.police_incidents._query_arcgis_features")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_geometry_column_is_queryable(mock_session_cls, mock_query, db_session):
    """The geometry column should support spatial queries."""
    mock_session_cls.return_value = db_session

    mock_query.return_value = [
        _make_feature(case_number="GEO-1", longitude=-78.639, latitude=35.780),
    ]

    fetch_raleigh_police_incidents(full_refresh=True)

    # Spatial query: find records within ~1km of the same point
    point_wkt = "SRID=4326;POINT(-78.639 35.780)"
    count = db_session.execute(
        select(func.count())
        .select_from(StagingRaleighPoliceIncident)
        .where(
            func.ST_DWithin(
                StagingRaleighPoliceIncident.location,
                func.ST_GeomFromEWKT(text(f"'{point_wkt}'")),
                0.01,
            )
        )
    ).scalar()
    assert count == 1
