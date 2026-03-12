"""Integration tests for Cary police incidents collector against a real PostGIS database."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import func, select, text

from pricepoint.data.geospatial.police_incidents import fetch_cary_police_incidents
from pricepoint.db.models import StagingCaryPoliceIncident

pytestmark = pytest.mark.integration


def _make_dataframe(*rows: dict[str, str]) -> pd.DataFrame:
    """Build a DataFrame matching what ODSClient.get_whole_dataframe() returns.

    Column names use the human-readable form that ODSClient produces
    (Title Case with spaces).  The collector normalises them internally.
    """
    defaults: dict[str, str] = {
        "Id": "24001001",
        "Incident Number": "24001001",
        "Crime Category": "LARCENY",
        "Crime Type": "LARCENY - FROM MV",
        "UCR": "230",
        "Map Reference": "P083",
        "Begin Date Of Occurrence": "2024-01-15T10:00:00+00:00",
        "Begin Time Of Occurrence": "10:00:00",
        "End Date Of Occurrence": "2024-01-15T12:00:00+00:00",
        "End Time Of Occurrence": "12:00:00",
        "Crime Day": "MONDAY",
        "Geo Code": "KILDAIRE FARM RD",
        "Location Category": "RESIDENTIAL",
        "District": "CPDS",
        "Beat Number": "050",
        "Neighborhood Id": "0024",
        "Apartment Complex": "",
        "Residential Subdivision": "LOCHMERE",
        "Subdivision Id": "0173",
        "PHX Activity Date": "2024-01-15",
        "PHX Record Status": "Active",
        "PHX Community": "Yes",
        "PHX Status": "Active",
        "Record": "114109",
        "Offense Category": "Larceny/Theft",
        "Violent Property": "Part I",
        "Timeframe": "Day",
        "Domestic": "N",
        "Total Incidents": "1",
        "Year": "2024",
        "Older Than Five Years From Now": "False",
        "Charge Count": "",
        "Lon": "-78.748",
        "Lat": "35.766",
    }
    records = []
    for row in rows:
        record = defaults.copy()
        record.update(row)
        records.append(record)
    return pd.DataFrame(records)


def _noop_geocode(*_args, **_kwargs):
    """No-op geocode function for tests that supply lat/lon directly."""
    return []


@patch("pricepoint.data.geospatial.police_incidents.ODSClient")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_records_persist_to_staging_table(mock_session_cls, mock_ods_cls, db_session):
    """Records should be persisted to the staging table with correct field values."""
    mock_session_cls.return_value = db_session

    mock_client = MagicMock()
    mock_client.get_whole_dataframe.return_value = _make_dataframe(
        {"Id": "INT_R1", "Incident Number": "INT001"}
    )
    mock_ods_cls.return_value = mock_client

    fetch_cary_police_incidents(full_refresh=True, geocode_fn=_noop_geocode)

    rows = db_session.execute(select(StagingCaryPoliceIncident)).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.api_id == "INT_R1"
    assert row.incident_number == "INT001"
    assert row.crime_category == "LARCENY"
    assert row.beat_number == "050"
    assert row.lon == pytest.approx(-78.748)
    assert row.lat == pytest.approx(35.766)
    assert row.location is not None


@patch("pricepoint.data.geospatial.police_incidents.ODSClient")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_full_refresh_truncates_before_load(mock_session_cls, mock_ods_cls, db_session):
    """Full refresh should remove old records and only keep new ones."""
    mock_session_cls.return_value = db_session

    # Seed an old record
    old = StagingCaryPoliceIncident(api_id="OLD_1", incident_number="OLD001")
    db_session.add(old)
    db_session.flush()

    mock_client = MagicMock()
    mock_client.get_whole_dataframe.return_value = _make_dataframe(
        {"Id": "NEW_1", "Incident Number": "NEW001"}
    )
    mock_ods_cls.return_value = mock_client

    fetch_cary_police_incidents(full_refresh=True, geocode_fn=_noop_geocode)

    rows = db_session.execute(select(StagingCaryPoliceIncident)).scalars().all()
    api_ids = {r.api_id for r in rows}
    assert "OLD_1" not in api_ids
    assert "NEW_1" in api_ids
    assert len(rows) == 1


@patch("pricepoint.data.geospatial.police_incidents.ODSClient")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_geometry_column_is_queryable(mock_session_cls, mock_ods_cls, db_session):
    """The geometry column should support spatial queries."""
    mock_session_cls.return_value = db_session

    mock_client = MagicMock()
    mock_client.get_whole_dataframe.return_value = _make_dataframe(
        {"Id": "GEO_1", "Lon": "-78.748", "Lat": "35.766"}
    )
    mock_ods_cls.return_value = mock_client

    fetch_cary_police_incidents(full_refresh=True, geocode_fn=_noop_geocode)

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
