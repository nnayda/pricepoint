"""Tests for TIGER/Line boundary shapefile collector."""

import io
import os
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import MultiPolygon, Polygon

from pricepoint.data.geospatial.tiger_boundaries import (
    _read_shapefile,
    _tiger_url,
    _to_multipolygon_wkb,
)


def _make_simple_polygon():
    """Create a simple square polygon for testing."""
    return Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])


def _make_simple_multipolygon():
    """Create a simple MultiPolygon for testing."""
    return MultiPolygon([_make_simple_polygon()])


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


# -- _tiger_url tests ---------------------------------------------------------


@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_tiger_url_state_level(mock_settings):
    """_tiger_url should build correct URL for state-level files."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )
    url = _tiger_url("BG", "37", "bg")
    assert url == "https://www2.census.gov/geo/tiger/TIGER2025/BG/tl_2025_37_bg.zip"


@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_tiger_url_national_file(mock_settings):
    """_tiger_url should build correct URL for national files."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
    )
    url = _tiger_url("COUNTY", "us", "county")
    assert url == "https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip"


# -- _to_multipolygon_wkb tests -----------------------------------------------


def test_to_multipolygon_wraps_polygon():
    """_to_multipolygon_wkb should wrap a Polygon into a MultiPolygon."""
    poly = _make_simple_polygon()
    result = _to_multipolygon_wkb(poly)
    assert result is not None


def test_to_multipolygon_passes_multipolygon():
    """_to_multipolygon_wkb should accept a MultiPolygon as-is."""
    mpoly = _make_simple_multipolygon()
    result = _to_multipolygon_wkb(mpoly)
    assert result is not None


# -- _read_shapefile tests ----------------------------------------------------


def test_read_shapefile_from_zip():
    """_read_shapefile should read a GeoDataFrame from zip bytes."""
    columns = {"NAME": ["Test"]}
    shapes = [_make_simple_polygon()]
    zip_bytes = _make_tiger_zip(columns, shapes)

    gdf = _read_shapefile(zip_bytes)
    assert len(gdf) == 1
    assert gdf.iloc[0]["NAME"] == "Test"


def test_read_shapefile_from_zip_missing_component():
    """_read_shapefile should raise an error if zip has no valid shapefile."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("readme.txt", b"not a shapefile")

    with pytest.raises((ValueError, RuntimeError, OSError)):
        _read_shapefile(zip_buf.getvalue())


# -- fetch_tiger_tracts tests -------------------------------------------------


@patch("pricepoint.data.geospatial.tiger_boundaries._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_boundaries.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_fetch_tiger_tracts_filters_by_county(mock_settings, mock_session_cls, mock_download):
    """fetch_tiger_tracts should only load records matching the configured county FIPS."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
        tiger_state_fips="37",
        tiger_county_fips="183",
    )

    columns = {
        "STATEFP": ["37", "37"],
        "COUNTYFP": ["183", "063"],
        "TRACTCE": ["050100", "050200"],
        "GEOID": ["37183050100", "37063050200"],
        "NAME": ["501", "502"],
        "NAMELSAD": ["Census Tract 501", "Census Tract 502"],
        "ALAND": [1000000, 2000000],
        "AWATER": [500, 300],
        "INTPTLAT": ["+35.7796", "+35.5000"],
        "INTPTLON": ["-078.6382", "-079.1000"],
        "FUNCSTAT": ["S", "S"],
        "MTFCC": ["G5020", "G5020"],
    }
    shapes = [_make_simple_polygon(), _make_simple_polygon()]
    mock_download.return_value = _make_tiger_zip(columns, shapes)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_tracts

    fetch_tiger_tracts()

    # Should only add records for county 183, not 063
    mock_session.add_all.assert_called_once()
    added_records = mock_session.add_all.call_args[0][0]
    assert len(added_records) == 1
    assert added_records[0].geoid == "37183050100"


@patch("pricepoint.data.geospatial.tiger_boundaries._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_boundaries.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_fetch_tiger_tracts_empty_result(mock_settings, mock_session_cls, mock_download):
    """fetch_tiger_tracts should handle empty results (no matching county)."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
        tiger_state_fips="37",
        tiger_county_fips="999",
    )

    columns = {
        "STATEFP": ["37"],
        "COUNTYFP": ["183"],
        "TRACTCE": ["050100"],
        "GEOID": ["37183050100"],
        "NAME": ["501"],
        "NAMELSAD": ["Census Tract 501"],
        "ALAND": [1000000],
        "AWATER": [500],
        "INTPTLAT": ["+35.7796"],
        "INTPTLON": ["-078.6382"],
        "FUNCSTAT": ["S"],
        "MTFCC": ["G5020"],
    }
    shapes = [_make_simple_polygon()]
    mock_download.return_value = _make_tiger_zip(columns, shapes)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_tracts

    fetch_tiger_tracts()

    # add_all should not have been called since no records match
    mock_session.add_all.assert_not_called()


@patch("pricepoint.data.geospatial.tiger_boundaries._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_boundaries.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_fetch_tiger_tracts_rollback_on_exception(mock_settings, mock_session_cls, mock_download):
    """fetch_tiger_tracts should rollback the session on exception."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
        tiger_state_fips="37",
        tiger_county_fips="183",
    )
    mock_download.side_effect = RuntimeError("Network error")

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_tracts

    with pytest.raises(RuntimeError, match="Network error"):
        fetch_tiger_tracts()

    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()


# -- fetch_tiger_school_districts tests ----------------------------------------


@patch("pricepoint.data.geospatial.tiger_boundaries._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_boundaries.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_fetch_school_districts_loads_all_types(mock_settings, mock_session_cls, mock_download):
    """fetch_tiger_school_districts should load all 3 district types."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
        tiger_state_fips="37",
        tiger_county_fips="183",
    )

    columns = {
        "STATEFP": ["37"],
        "GEOID": ["3700001"],
        "NAME": ["Test District"],
        "LSAD": ["00"],
        "LOGRADE": ["PK"],
        "HIGRADE": ["12"],
        "ALAND": [5000000],
        "AWATER": [1000],
        "INTPTLAT": ["+35.7796"],
        "INTPTLON": ["-078.6382"],
        "FUNCSTAT": ["A"],
        "MTFCC": ["G5400"],
        "SDTYP": [""],
    }
    zip_bytes = _make_tiger_zip(columns, [_make_simple_polygon()])
    mock_download.return_value = zip_bytes

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_school_districts

    fetch_tiger_school_districts()

    # Should be called 3 times (once per district type), each adding records
    assert mock_session.add_all.call_count == 3

    # Check that each call had the correct district_type
    types_seen = set()
    for call in mock_session.add_all.call_args_list:
        for record in call[0][0]:
            types_seen.add(record.district_type)
    assert types_seen == {"elementary", "secondary", "unified"}


@patch("pricepoint.data.geospatial.tiger_boundaries._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_boundaries.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_fetch_school_districts_handles_404(mock_settings, mock_session_cls, mock_download):
    """fetch_tiger_school_districts should skip missing district types (404)."""
    import httpx

    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
        tiger_state_fips="37",
        tiger_county_fips="183",
    )

    columns = {
        "STATEFP": ["37"],
        "GEOID": ["3700001"],
        "NAME": ["Test District"],
        "LSAD": ["00"],
        "LOGRADE": ["PK"],
        "HIGRADE": ["12"],
        "ALAND": [5000000],
        "AWATER": [1000],
        "INTPTLAT": ["+35.7796"],
        "INTPTLON": ["-078.6382"],
        "FUNCSTAT": ["A"],
        "MTFCC": ["G5400"],
        "SDTYP": [""],
    }
    zip_bytes = _make_tiger_zip(columns, [_make_simple_polygon()])

    # ELSD returns 404, SCSD and UNSD succeed
    mock_response_404 = MagicMock()
    mock_response_404.status_code = 404
    http_error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response_404)

    mock_download.side_effect = [http_error, zip_bytes, zip_bytes]

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_school_districts

    fetch_tiger_school_districts()

    # Only 2 district types should have been loaded (ELSD skipped)
    assert mock_session.add_all.call_count == 2


# -- fetch_tiger_counties tests -----------------------------------------------


@patch("pricepoint.data.geospatial.tiger_boundaries._download_tiger_zip")
@patch("pricepoint.data.geospatial.tiger_boundaries.SessionLocal")
@patch("pricepoint.data.geospatial.tiger_boundaries.get_settings")
def test_fetch_tiger_counties_dual_filter(mock_settings, mock_session_cls, mock_download):
    """fetch_tiger_counties should filter by both state and county FIPS."""
    mock_settings.return_value = MagicMock(
        tiger_base_url="https://www2.census.gov/geo/tiger",
        tiger_year=2025,
        tiger_state_fips="37",
        tiger_county_fips="183",
    )

    columns = {
        "STATEFP": ["37", "37", "06"],
        "COUNTYFP": ["183", "063", "183"],
        "COUNTYNS": ["01008591", "01008557", "00277310"],
        "GEOID": ["37183", "37063", "06183"],
        "NAME": ["Wake", "Durham", "Test CA"],
        "NAMELSAD": ["Wake County", "Durham County", "Test CA County"],
        "LSAD": ["06", "06", "06"],
        "CLASSFP": ["H1", "H1", "H1"],
        "ALAND": [2200000000, 750000000, 100000000],
        "AWATER": [50000000, 20000000, 1000000],
        "INTPTLAT": ["+35.7796", "+36.0000", "+34.0000"],
        "INTPTLON": ["-078.6382", "-078.9000", "-118.0000"],
        "FUNCSTAT": ["A", "A", "A"],
        "MTFCC": ["G4020", "G4020", "G4020"],
        "CSAFP": ["", "", ""],
        "CBSAFP": ["39580", "20500", ""],
        "METDIVFP": ["", "", ""],
    }
    shapes = [_make_simple_polygon() for _ in range(3)]
    mock_download.return_value = _make_tiger_zip(columns, shapes)

    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    from pricepoint.data.geospatial.tiger_boundaries import fetch_tiger_counties

    fetch_tiger_counties()

    # Only Wake County (state=37, county=183) should match
    mock_session.add_all.assert_called_once()
    added_records = mock_session.add_all.call_args[0][0]
    assert len(added_records) == 1
    assert added_records[0].geoid == "37183"
    assert added_records[0].name == "Wake"
