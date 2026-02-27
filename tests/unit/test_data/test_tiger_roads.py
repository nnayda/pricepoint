"""Tests for TIGER/Line road shapefile collector."""

import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiLineString

from pricepoint.data.geospatial.tiger_roads import (
    _read_shapefile,
    _tiger_road_url,
    _to_multilinestring_wkb,
)


def _make_simple_linestring():
    """Create a simple line for testing."""
    return LineString([(0, 0), (1, 1), (2, 0)])


def _make_simple_multilinestring():
    """Create a simple MultiLineString for testing."""
    return MultiLineString([[(0, 0), (1, 1)], [(2, 2), (3, 3)]])


def _make_tiger_zip(columns, data):
    """Build an in-memory zip containing a shapefile from a GeoDataFrame.

    Args:
        columns: dict mapping column names to lists of values (excluding geometry).
        data: list of shapely geometries for the geometry column.

    Returns:
        bytes of the zip archive.
    """
    gdf = gpd.GeoDataFrame(columns, geometry=data, crs="EPSG:4326")

    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "test.shp")
        gdf.to_file(shp_path, driver="ESRI Shapefile")

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for fname in os.listdir(tmpdir):
                with open(os.path.join(tmpdir, fname), "rb") as f:
                    zf.writestr(fname, f.read())

        return zip_buf.getvalue()


# -- _tiger_road_url tests ---------------------------------------------------


@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_tiger_road_url_builds_correct_url(mock_settings):
    """_tiger_road_url should build correct URL for state-level PRISECROADS files."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )
    url = _tiger_road_url("37")
    assert url == (
        "https://www2.census.gov/geo/tiger/TIGER2025/PRISECROADS/tl_2025_37_prisecroads.zip"
    )


@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_tiger_road_url_uses_configured_year(mock_settings):
    """_tiger_road_url should use the configured tiger_year."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2024,
    )
    url = _tiger_road_url("06")
    assert "TIGER2024" in url
    assert "06_prisecroads" in url


# -- _to_multilinestring_wkb tests -------------------------------------------


def test_to_multilinestring_wraps_linestring():
    """_to_multilinestring_wkb should wrap a LineString into a MultiLineString."""
    line = _make_simple_linestring()
    result = _to_multilinestring_wkb(line)
    assert result is not None


def test_to_multilinestring_passes_multilinestring():
    """_to_multilinestring_wkb should accept a MultiLineString as-is."""
    mline = _make_simple_multilinestring()
    result = _to_multilinestring_wkb(mline)
    assert result is not None


# -- _read_shapefile tests ----------------------------------------------------


def test_read_shapefile_from_zip():
    """_read_shapefile should read a GeoDataFrame from zip bytes."""
    columns = {"LINEARID": ["1101234567890"], "FULLNAME": ["I- 40"]}
    shapes = [_make_simple_linestring()]
    zip_bytes = _make_tiger_zip(columns, shapes)

    gdf = _read_shapefile(zip_bytes)
    assert len(gdf) == 1
    assert gdf.iloc[0]["FULLNAME"] == "I- 40"


def test_read_shapefile_from_zip_missing_component():
    """_read_shapefile should raise an error if zip has no valid shapefile."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("readme.txt", b"not a shapefile")

    with pytest.raises((ValueError, RuntimeError, OSError)):
        _read_shapefile(zip_buf.getvalue())


# -- fetch_roads tests -------------------------------------------------------


@patch("pricepoint.data.geospatial.tiger_roads._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_fetch_roads_loads_records(mock_settings, mock_session_cls, mock_download):
    """fetch_roads should load all road records from the state file."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )

    columns = {
        "LINEARID": ["1101234567890", "1201234567891"],
        "FULLNAME": ["I- 40", "US Hwy 70"],
        "RTTYP": ["I", "U"],
        "MTFCC": ["S1100", "S1200"],
    }
    shapes = [_make_simple_linestring(), _make_simple_linestring()]
    mock_download.return_value = _make_tiger_zip(columns, shapes)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_roads import fetch_roads

    fetch_roads(state_fips="37")

    mock_session.add_all.assert_called_once()
    added_records = mock_session.add_all.call_args[0][0]
    assert len(added_records) == 2
    linearids = {r.linearid for r in added_records}
    assert linearids == {"1101234567890", "1201234567891"}


@patch("pricepoint.data.geospatial.tiger_roads._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_fetch_roads_single_state(mock_settings, mock_session_cls, mock_download):
    """fetch_roads with state_fips should download only that state."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )

    columns = {
        "LINEARID": ["1101234567890"],
        "FULLNAME": ["I- 40"],
        "RTTYP": ["I"],
        "MTFCC": ["S1100"],
    }
    shapes = [_make_simple_linestring()]
    mock_download.return_value = _make_tiger_zip(columns, shapes)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_roads import fetch_roads

    fetch_roads(state_fips="37")

    mock_download.assert_called_once()
    assert "37" in mock_download.call_args[0][0]


@patch("pricepoint.data.geospatial.tiger_roads._download_with_year_fallback")
@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_fetch_roads_rollback_on_exception(mock_settings, mock_session_cls, mock_download):
    """fetch_roads should rollback the session on exception."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )
    mock_download.side_effect = RuntimeError("Network error")

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_roads import fetch_roads

    with pytest.raises(RuntimeError, match="Network error"):
        fetch_roads(state_fips="37")

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


@patch("pricepoint.data.geospatial.tiger_roads._download_with_year_fallback")
@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_fetch_roads_skips_unavailable_state(mock_settings, mock_session_cls, mock_download):
    """fetch_roads should skip states where download returns None."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )

    columns = {
        "LINEARID": ["1101234567890"],
        "FULLNAME": ["I- 40"],
        "RTTYP": ["I"],
        "MTFCC": ["S1100"],
    }
    zip_bytes = _make_tiger_zip(columns, [_make_simple_linestring()])

    # First state unavailable, second succeeds
    mock_download.side_effect = [None, zip_bytes]

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_roads import fetch_roads

    with patch("pricepoint.data.geospatial.tiger_roads.US_STATE_FIPS", ["01", "06"]):
        fetch_roads()

    # Only second state loaded records
    mock_session.add_all.assert_called_once()
    added_records = mock_session.add_all.call_args[0][0]
    assert len(added_records) == 1


@patch("pricepoint.data.geospatial.tiger_roads._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_roads.get_settings")
def test_fetch_roads_commits_once(mock_settings, mock_session_cls, mock_download):
    """fetch_roads should use a single transaction (one commit at the end)."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )

    columns = {
        "LINEARID": ["1101234567890"],
        "FULLNAME": ["I- 40"],
        "RTTYP": ["I"],
        "MTFCC": ["S1100"],
    }
    shapes = [_make_simple_linestring()]
    mock_download.return_value = _make_tiger_zip(columns, shapes)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_roads import fetch_roads

    fetch_roads(state_fips="37")

    # Single transaction: one commit at the end (delete + inserts together)
    mock_session.commit.assert_called_once()


# -- verify_roads tests -------------------------------------------------------


@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
def test_verify_roads_passes_with_records(mock_session_cls):
    """verify_roads should pass when records exist."""
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_session.execute.return_value.scalar.return_value = 42

    from pricepoint.data.geospatial.tiger_roads import verify_roads

    verify_roads()  # Should not raise

    mock_session.close.assert_called_once()


@patch("pricepoint.data.geospatial.tiger_roads.SessionLocal")
def test_verify_roads_raises_when_empty(mock_session_cls):
    """verify_roads should raise RuntimeError when no records found."""
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_session.execute.return_value.scalar.return_value = 0

    from pricepoint.data.geospatial.tiger_roads import verify_roads

    with pytest.raises(RuntimeError, match="No records found in roads"):
        verify_roads()

    mock_session.close.assert_called_once()
