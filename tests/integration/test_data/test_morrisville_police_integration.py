"""Integration tests for Morrisville police incidents collector against a real PostGIS database."""

from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text

from pricepoint.data.geospatial.police_incidents import (
    fetch_morrisville_police_incidents,
)
from pricepoint.db.models import StagingMorrisvillePoliceIncident

pytestmark = pytest.mark.integration

_CSV_HEADERS = (
    "date_rept;date_occu;dow1;monthstamp;yearstamp;inci_id;offense;"
    "street;city;state;zip;neighborhd;subdivisn;tract;zone;district;"
    "asst_offcr;area"
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
        "date_rept": "2024-01-15T10:00:00+00:00",
        "date_occu": "2024-01-15T08:00:00+00:00",
        "dow1": "Monday",
        "monthstamp": "January",
        "yearstamp": "2024",
        "inci_id": "24001001",
        "offense": "LARCENY - FROM MOTOR VEHICLE",
        "street": "TOWN HALL DR",
        "city": "MORRISVILLE",
        "state": "NC",
        "zip": "27560",
        "neighborhd": "",
        "subdivisn": "0009",
        "tract": "P132",
        "zone": "2",
        "district": "MPD1",
        "asst_offcr": "1",
        "area": "35.812711, -78.819843",
    }
    base.update(overrides)
    return base


@patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_records_persist_to_staging_table(
    mock_session_cls, mock_get_dataset, db_session
):
    """Records should be persisted to the staging table with correct field values."""
    mock_session_cls.return_value = db_session

    csv_text = _make_csv(_make_record(inci_id="INT_M1", offense="VANDALISM"))
    mock_get_dataset.return_value = csv_text

    fetch_morrisville_police_incidents(full_refresh=True)

    rows = (
        db_session.execute(select(StagingMorrisvillePoliceIncident)).scalars().all()
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.inci_id == "INT_M1"
    assert row.offense == "VANDALISM"
    assert row.city == "MORRISVILLE"
    assert row.district == "MPD1"
    assert row.lat == pytest.approx(35.812711)
    assert row.lon == pytest.approx(-78.819843)
    assert row.location is not None


@patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_full_refresh_truncates_before_load(
    mock_session_cls, mock_get_dataset, db_session
):
    """Full refresh should remove old records and only keep new ones."""
    mock_session_cls.return_value = db_session

    # Seed an old record
    old = StagingMorrisvillePoliceIncident(inci_id="OLD_1", offense="OLD")
    db_session.add(old)
    db_session.flush()

    # Mock returns a different record
    csv_text = _make_csv(_make_record(inci_id="NEW_1", offense="NEW"))
    mock_get_dataset.return_value = csv_text

    fetch_morrisville_police_incidents(full_refresh=True)

    rows = (
        db_session.execute(select(StagingMorrisvillePoliceIncident)).scalars().all()
    )
    inci_ids = {r.inci_id for r in rows}
    assert "OLD_1" not in inci_ids
    assert "NEW_1" in inci_ids
    assert len(rows) == 1


@patch("pricepoint.data.geospatial.police_incidents.get_whole_dataset")
@patch("pricepoint.data.geospatial.police_incidents.SessionLocal")
def test_geometry_column_is_queryable(
    mock_session_cls, mock_get_dataset, db_session
):
    """The geometry column should support spatial queries."""
    mock_session_cls.return_value = db_session

    csv_text = _make_csv(
        _make_record(inci_id="GEO_1", area="35.812711, -78.819843")
    )
    mock_get_dataset.return_value = csv_text

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
