"""Integration tests for Cary police incidents collector against a real PostGIS database."""

from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text

from pricepoint.data.geospatial.police_incidents import fetch_cary_police_incidents
from pricepoint.db.models import StagingCaryPoliceIncident

pytestmark = pytest.mark.integration

_CSV_HEADERS = (
    "id;incident_number;crime_category;crime_type;ucr;map_reference;"
    "date_from;from_time;date_to;to_time;crimeday;geocode;"
    "location_category;district;beat_number;neighborhd_id;"
    "apartment_complex;residential_subdivision;subdivisn_id;"
    "activity_date;phxrecordstatus;phxcommunity;phxstatus;"
    "record;offensecategory;violentproperty;timeframe;domestic;"
    "total_incidents;year;older_than_five_years_from_now;chrgcnt;"
    "lon;lat"
)


def _make_csv(*rows: dict[str, str]) -> str:
    """Build a semicolon-delimited CSV string with the standard headers."""
    lines = [_CSV_HEADERS]
    for row in rows:
        fields = _CSV_HEADERS.split(";")
        lines.append(";".join(row.get(f, "") for f in fields))
    return "\n".join(lines)


def _make_record(**overrides: str) -> dict[str, str]:
    """Return a minimal CSV-style record dict with optional overrides."""
    base: dict[str, str] = {
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
        "beat_number": "050",
        "neighborhd_id": "0024",
        "apartment_complex": "",
        "residential_subdivision": "LOCHMERE",
        "subdivisn_id": "0173",
        "activity_date": "2024-01-15",
        "phxrecordstatus": "Active",
        "phxcommunity": "Yes",
        "phxstatus": "Active",
        "record": "114109",
        "offensecategory": "Larceny/Theft",
        "violentproperty": "Part I",
        "timeframe": "Day",
        "domestic": "N",
        "total_incidents": "1",
        "year": "2024",
        "older_than_five_years_from_now": "False",
        "chrgcnt": "",
        "lon": "-78.748",
        "lat": "35.766",
    }
    base.update(overrides)
    return base


@patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_records_persist_to_staging_table(mock_session_cls, mock_get_dataset, db_session):
    """Records should be persisted to the staging table with correct field values."""
    mock_session_cls.return_value = db_session

    csv_text = _make_csv(_make_record(id="INT_R1", incident_number="INT001"))
    mock_get_dataset.return_value = csv_text

    fetch_cary_police_incidents(full_refresh=True)

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


@patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_full_refresh_truncates_before_load(mock_session_cls, mock_get_dataset, db_session):
    """Full refresh should remove old records and only keep new ones."""
    mock_session_cls.return_value = db_session

    # Seed an old record
    old = StagingCaryPoliceIncident(api_id="OLD_1", incident_number="OLD001")
    db_session.add(old)
    db_session.flush()

    # Mock returns a different record
    csv_text = _make_csv(_make_record(id="NEW_1", incident_number="NEW001"))
    mock_get_dataset.return_value = csv_text

    fetch_cary_police_incidents(full_refresh=True)

    rows = db_session.execute(select(StagingCaryPoliceIncident)).scalars().all()
    api_ids = {r.api_id for r in rows}
    assert "OLD_1" not in api_ids
    assert "NEW_1" in api_ids
    assert len(rows) == 1


@patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_geometry_column_is_queryable(mock_session_cls, mock_get_dataset, db_session):
    """The geometry column should support spatial queries."""
    mock_session_cls.return_value = db_session

    csv_text = _make_csv(_make_record(id="GEO_1", lon="-78.748", lat="35.766"))
    mock_get_dataset.return_value = csv_text

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
