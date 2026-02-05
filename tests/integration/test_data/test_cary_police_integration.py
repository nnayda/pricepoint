"""Integration tests for Cary police incidents collector against a real PostGIS database."""

from unittest.mock import patch

import httpx
import pytest
import respx
from sqlalchemy import func, select, text

from pricepoint.data.geospatial.police_incidents import fetch_cary_police_incidents
from pricepoint.db.models import StagingCaryPoliceIncident

pytestmark = pytest.mark.integration

_API_URL = "https://data.townofcary.org/api/explore/v2.1/catalog/datasets/cpd-incidents/records"


def _make_record(**overrides):
    """Return a minimal API record dict with optional overrides."""
    base = {
        "id": "24001001",
        "incident_number": "24001001",
        "crime_category": "LARCENY",
        "crime_type": "LARCENY - FROM MV",
        "ucr": "230",
        "map_reference": "P083",
        "date_from": "2024-01-15T10:00:00+00:00",
        "from_time": "10:00:00",
        "date_to": "2024-01-15T12:00:00+00:00",
        "to_time": "12:00:00",
        "crimeday": "MONDAY",
        "geocode": "KILDAIRE FARM RD",
        "location_category": "RESIDENTIAL",
        "district": "CPDS",
        "beat_number": 50,
        "neighborhd_id": "0024",
        "apartment_complex": None,
        "residential_subdivision": "LOCHMERE",
        "subdivisn_id": "0173",
        "activity_date": "2024-01-15",
        "phxrecordstatus": "Active",
        "phxcommunity": "Yes",
        "phxstatus": "Active",
        "record": 114109,
        "offensecategory": "Larceny/Theft",
        "violentproperty": "Part I",
        "timeframe": "Day",
        "domestic": "N",
        "total_incidents": 1,
        "year": "2024",
        "older_than_five_years_from_now": "False",
        "chrgcnt": None,
        "lon": -78.748,
        "lat": 35.766,
        "location": {"lon": -78.748, "lat": 35.766},
    }
    base.update(overrides)
    return base


@respx.mock
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_records_persist_to_staging_table(mock_session_cls, db_session):
    """Records should be persisted to the staging table with correct field values."""
    mock_session_cls.return_value = db_session

    records = [_make_record(id="INT_R1", incident_number="INT001")]
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json={"total_count": 1, "results": records})
    )

    fetch_cary_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingCaryPoliceIncident)).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.api_id == "INT_R1"
    assert row.incident_number == "INT001"
    assert row.crime_category == "LARCENY"
    assert row.beat_number == "50"
    assert row.lon == pytest.approx(-78.748)
    assert row.lat == pytest.approx(35.766)
    assert row.location is not None


@respx.mock
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_full_refresh_truncates_before_load(mock_session_cls, db_session):
    """Full refresh should remove old records and only keep new ones."""
    mock_session_cls.return_value = db_session

    # Seed an old record
    old = StagingCaryPoliceIncident(api_id="OLD_1", incident_number="OLD001")
    db_session.add(old)
    db_session.flush()

    # Mock API returns a different record
    new_records = [_make_record(id="NEW_1", incident_number="NEW001")]
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json={"total_count": 1, "results": new_records})
    )

    fetch_cary_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingCaryPoliceIncident)).scalars().all()
    api_ids = {r.api_id for r in rows}
    assert "OLD_1" not in api_ids
    assert "NEW_1" in api_ids
    assert len(rows) == 1


@respx.mock
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_geometry_column_is_queryable(mock_session_cls, db_session):
    """The geometry column should support spatial queries."""
    mock_session_cls.return_value = db_session

    records = [_make_record(id="GEO_1", lon=-78.748, lat=35.766)]
    respx.get(_API_URL).mock(
        return_value=httpx.Response(200, json={"total_count": 1, "results": records})
    )

    fetch_cary_police_incidents(full_refresh=True)

    # Spatial query: find records within 1000 meters of the same point
    point_wkt = "SRID=4326;POINT(-78.748 35.766)"
    count = db_session.execute(
        select(func.count())
        .select_from(StagingCaryPoliceIncident)
        .where(
            func.ST_DWithin(
                StagingCaryPoliceIncident.location,
                func.ST_GeomFromEWKT(text(f"'{point_wkt}'")),
                0.01,  # ~1km in degrees
            )
        )
    ).scalar()
    assert count == 1
