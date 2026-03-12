"""Integration tests for Morrisville police incidents collector against a real PostGIS database."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import func, select, text

from pricepoint.data.geospatial.police_incidents import (
    fetch_morrisville_police_incidents,
)
from pricepoint.db.models import StagingMorrisvillePoliceIncident

pytestmark = pytest.mark.integration


def _make_dataframe(*rows: dict[str, str]) -> pd.DataFrame:
    """Build a DataFrame matching what ODSClient.get_whole_dataframe() returns.

    Column names use the human-readable form that ODSClient produces
    (Title Case with spaces).  The collector normalises them internally.
    """
    defaults: dict[str, str] = {
        "Incident Id": "24001001",
        "Offense": "LARCENY - FROM MOTOR VEHICLE",
        "Date Reported": "2024-01-15T10:00:00+00:00",
        "Date Occurred": "2024-01-15T08:00:00+00:00",
        "Day Of Week": "Monday",
        "Month": "January",
        "Year": "2024",
        "Street": "TOWN HALL DR",
        "City": "MORRISVILLE",
        "State": "NC",
        "Zip": "27560",
        "Neighborhood": "",
        "Subdivision": "0009",
        "Tract": "P132",
        "Zone": "2",
        "District": "MPD1",
        "# Of Asst Officers": "1",
        "Area": "35.812711, -78.819843",
    }
    records = []
    for row in rows:
        record = defaults.copy()
        record.update(row)
        records.append(record)
    return pd.DataFrame(records)


@patch("pricepoint.data.geospatial.police_incidents.ODSClient")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_records_persist_to_staging_table(mock_session_cls, mock_ods_cls, db_session):
    """Records should be persisted to the staging table with correct field values."""
    mock_session_cls.return_value = db_session

    mock_client = MagicMock()
    mock_client.get_whole_dataframe.return_value = _make_dataframe(
        {"Incident Id": "INT_M1", "Offense": "VANDALISM"}
    )
    mock_ods_cls.return_value = mock_client

    fetch_morrisville_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingMorrisvillePoliceIncident)).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.inci_id == "INT_M1"
    assert row.offense == "VANDALISM"
    assert row.city == "MORRISVILLE"
    assert row.district == "MPD1"
    assert row.lat == pytest.approx(35.812711)
    assert row.lon == pytest.approx(-78.819843)
    assert row.location is not None


@patch("pricepoint.data.geospatial.police_incidents.ODSClient")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_full_refresh_truncates_before_load(mock_session_cls, mock_ods_cls, db_session):
    """Full refresh should remove old records and only keep new ones."""
    mock_session_cls.return_value = db_session

    # Seed an old record
    old = StagingMorrisvillePoliceIncident(inci_id="OLD_1", offense="OLD")
    db_session.add(old)
    db_session.flush()

    mock_client = MagicMock()
    mock_client.get_whole_dataframe.return_value = _make_dataframe(
        {"Incident Id": "NEW_1", "Offense": "NEW"}
    )
    mock_ods_cls.return_value = mock_client

    fetch_morrisville_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingMorrisvillePoliceIncident)).scalars().all()
    inci_ids = {r.inci_id for r in rows}
    assert "OLD_1" not in inci_ids
    assert "NEW_1" in inci_ids
    assert len(rows) == 1


@patch("pricepoint.data.geospatial.police_incidents.ODSClient")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_geometry_column_is_queryable(mock_session_cls, mock_ods_cls, db_session):
    """The geometry column should support spatial queries."""
    mock_session_cls.return_value = db_session

    mock_client = MagicMock()
    mock_client.get_whole_dataframe.return_value = _make_dataframe(
        {"Incident Id": "GEO_1", "Area": "35.812711, -78.819843"}
    )
    mock_ods_cls.return_value = mock_client

    fetch_morrisville_police_incidents(full_refresh=True)

    # Spatial query: find records within ~1km of the same point
    point_wkt = "SRID=4326;POINT(-78.819843 35.812711)"
    count = db_session.execute(
        select(func.count())
        .select_from(StagingMorrisvillePoliceIncident)
        .where(
            func.ST_DWithin(
                StagingMorrisvillePoliceIncident.location,
                func.ST_GeomFromEWKT(text(f"'{point_wkt}'")),
                0.01,
            )
        )
    ).scalar()
    assert count == 1
