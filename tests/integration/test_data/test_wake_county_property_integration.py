"""Integration tests for Wake County property data collector using actual fixture."""

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import func, select

from pricepoint.data.housing.wake_county_property import (
    _parse_fwf_data,
    fetch_wake_county_property_data,
)
from pricepoint.db.models import StagingWakeCountyPropertyData

FIXTURE_PATH = Path(__file__).parent.parent.parent / "fixtures" / "wake_county_property_sample.txt"


def _make_test_zip_from_fixture() -> bytes:
    """Create in-memory ZIP file from actual fixture.

    Returns:
        ZIP file as bytes
    """
    with open(FIXTURE_PATH, "rb") as f:
        fixture_bytes = f.read()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("RealEstData.txt", fixture_bytes)
    return zip_buf.getvalue()


def test_parse_actual_fixture():
    """Test parsing actual 100-line fixture file."""
    with open(FIXTURE_PATH, encoding="latin1") as f:
        txt_content = f.read()

    df = _parse_fwf_data(txt_content)

    # Verify record count
    assert len(df) == 100

    # Verify columns exist
    assert "REID" in df.columns
    assert "Owner 1" in df.columns
    assert "Year Built" in df.columns
    assert "Heated Area" in df.columns
    assert "Total Sale Price" in df.columns
    assert "Physical City" in df.columns
    assert "Physical Zip Code" in df.columns

    # Verify sample values from first record
    first_row = df.iloc[0]
    assert first_row["REID"] is not None
    assert first_row["Physical City"] is not None or first_row["Physical Zip Code"] is not None


@patch("pricepoint.data.housing.wake_county_property._download_zip")
@patch("pricepoint.data.housing.wake_county_property._discover_zip_url")
def test_end_to_end_with_actual_fixture(mock_discover, mock_download, db_session):
    """Test full collection with actual fixture and real database.

    Uses testcontainers db_session fixture and actual 100-line fixture.
    """

    # Mock SessionLocal to use test database session
    with patch(
        "pricepoint.data.housing.wake_county_property.SessionLocal",
        return_value=db_session,
    ):
        # Mock discovery and download to return fixture ZIP
        mock_discover.return_value = "https://services.wake.gov/realdata_extracts/RealEstData.zip"
        zip_bytes = _make_test_zip_from_fixture()
        mock_download.return_value = zip_bytes

        # Execute
        fetch_wake_county_property_data()

    # Verify records in DB
    count = db_session.execute(
        select(func.count()).select_from(StagingWakeCountyPropertyData)
    ).scalar()
    assert count == 100

    # Verify sample record
    first_record = db_session.execute(select(StagingWakeCountyPropertyData).limit(1)).scalar_one()
    assert first_record.reid is not None
    assert first_record.id is not None
    assert first_record.loaded_at is not None


@patch("pricepoint.data.housing.wake_county_property._download_zip")
@patch("pricepoint.data.housing.wake_county_property._discover_zip_url")
def test_truncate_and_reload_behavior(mock_discover, mock_download, db_session):
    """Test that fetch truncates existing data before reload."""

    # Mock SessionLocal to use test database session
    with patch(
        "pricepoint.data.housing.wake_county_property.SessionLocal",
        return_value=db_session,
    ):
        # Mock discovery and download to return fixture ZIP
        mock_discover.return_value = "https://services.wake.gov/realdata_extracts/RealEstData.zip"
        zip_bytes = _make_test_zip_from_fixture()
        mock_download.return_value = zip_bytes

        # Execute first load
        fetch_wake_county_property_data()

        # Verify initial count
        count1 = db_session.execute(
            select(func.count()).select_from(StagingWakeCountyPropertyData)
        ).scalar()
        assert count1 == 100

        # Execute second load (should truncate and reload)
        fetch_wake_county_property_data()

        # Verify count is still 100 (not 200)
        count2 = db_session.execute(
            select(func.count()).select_from(StagingWakeCountyPropertyData)
        ).scalar()
        assert count2 == 100
