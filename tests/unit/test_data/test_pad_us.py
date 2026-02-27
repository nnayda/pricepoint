"""Tests for PAD-US greenspace collector."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as real_gpd
import pandas as pd
import pytest
from shapely.geometry import MultiPolygon, Polygon

from pricepoint.data.geospatial.pad_us import (
    _ALLOWED_PUB_ACCESS,
    _EXCLUDED_DES_TP,
    _parse_pad_us_row,
    _should_include,
    _to_multipolygon_wkb,
    fetch_pad_us,
    verify_pad_us,
)


# ---------------------------------------------------------------------------
# _should_include filter tests
# ---------------------------------------------------------------------------
class TestShouldInclude:
    def test_open_access_park_included(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "OA", "Des_Tp": "NP"}.get(k)
        assert _should_include(row) is True

    def test_restricted_access_included(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "RA", "Des_Tp": "SP"}.get(k)
        assert _should_include(row) is True

    def test_closed_access_excluded(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "XA", "Des_Tp": "NP"}.get(k)
        assert _should_include(row) is False

    def test_unknown_access_excluded(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "UK", "Des_Tp": "SP"}.get(k)
        assert _should_include(row) is False

    def test_marine_designation_excluded(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "OA", "Des_Tp": "MPA"}.get(k)
        assert _should_include(row) is False

    def test_research_natural_area_excluded(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "OA", "Des_Tp": "RNA"}.get(k)
        assert _should_include(row) is False

    def test_marine_reserve_excluded(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "OA", "Des_Tp": "MR"}.get(k)
        assert _should_include(row) is False

    def test_unknown_designation_excluded(self):
        row = MagicMock()
        row.get = lambda k: {"Pub_Access": "RA", "Des_Tp": "UNKW"}.get(k)
        assert _should_include(row) is False

    def test_allowed_pub_access_values(self):
        assert {"OA", "RA"} == _ALLOWED_PUB_ACCESS

    def test_excluded_designation_types(self):
        assert {"MPA", "MR", "RNA", "UNKW"} == _EXCLUDED_DES_TP


# ---------------------------------------------------------------------------
# _parse_pad_us_row tests
# ---------------------------------------------------------------------------
class TestParsePadUsRow:
    def _make_row(self, overrides=None):
        data = {
            "FID": 12345,
            "Unit_Nm": "Yellowstone National Park",
            "GIS_Acres": 2219790.71,
            "Mang_Type": "FED",
            "Mang_Name": "NPS",
            "Des_Tp": "NP",
            "Pub_Access": "OA",
            "GAP_Sts": 1,
            "d_State_Nm": "Wyoming",
            "Category": "Fee",
        }
        if overrides:
            data.update(overrides)
        row = MagicMock()
        row.get = lambda k: data.get(k)
        row.name = 0  # DataFrame index
        row.geometry = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
        return row

    def test_core_fields_mapped(self):
        result = _parse_pad_us_row(self._make_row())
        assert result["source_id"] == 12345
        assert result["name"] == "Yellowstone National Park"
        assert result["gis_acres"] == 2219790.71
        assert result["manager_type"] == "FED"
        assert result["manager_name"] == "NPS"
        assert result["designation_type"] == "NP"
        assert result["pub_access"] == "OA"
        assert result["gap_sts"] == 1
        assert result["state_name"] == "Wyoming"
        assert result["category"] == "Fee"

    def test_geometry_converted_to_wkb(self):
        result = _parse_pad_us_row(self._make_row())
        assert result["geom"] is not None

    def test_missing_gis_acres(self):
        result = _parse_pad_us_row(self._make_row({"GIS_Acres": None}))
        assert result["gis_acres"] is None

    def test_missing_gap_sts(self):
        result = _parse_pad_us_row(self._make_row({"GAP_Sts": None}))
        assert result["gap_sts"] is None

    def test_empty_gap_sts(self):
        result = _parse_pad_us_row(self._make_row({"GAP_Sts": ""}))
        assert result["gap_sts"] is None

    def test_fid_fallback_to_index(self):
        """When FID is None, use DataFrame row index as source_id."""
        row = self._make_row({"FID": None})
        row.name = 42
        result = _parse_pad_us_row(row)
        assert result["source_id"] == 42


# ---------------------------------------------------------------------------
# _to_multipolygon_wkb tests
# ---------------------------------------------------------------------------
class TestToMultipolygonWkb:
    def test_polygon_promoted_to_multipolygon(self):
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        result = _to_multipolygon_wkb(poly)
        assert result is not None

    def test_multipolygon_unchanged(self):
        mp = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
        result = _to_multipolygon_wkb(mp)
        assert result is not None

    def test_none_geometry(self):
        assert _to_multipolygon_wkb(None) is None


# ---------------------------------------------------------------------------
# fetch_pad_us tests
# ---------------------------------------------------------------------------
class TestFetchPadUs:
    @patch("pricepoint.data.geospatial.pad_us.gpd")
    @patch("pricepoint.data.geospatial.pad_us.zipfile.ZipFile")
    @patch("pricepoint.data.geospatial.pad_us.httpx")
    @patch("pricepoint.data.geospatial.pad_us.SessionLocal")
    @patch("pricepoint.data.geospatial.pad_us.get_settings")
    def test_fetch_upserts_filtered_rows(
        self, mock_settings, mock_session_cls, mock_httpx, mock_zipfile, mock_gpd
    ):
        settings = MagicMock()
        settings.pad_us_download_url = "http://example.com/padus.zip"
        settings.pad_us_layer_name = "PADUS4_1Fee"
        mock_settings.return_value = settings

        session = MagicMock()
        mock_session_cls.return_value = session

        # Mock httpx streaming
        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/zip"}
        mock_resp.iter_bytes.return_value = [b"fake"]
        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__ = MagicMock(return_value=mock_resp)
        mock_stream_cm.__exit__ = MagicMock(return_value=False)
        mock_httpx.stream.return_value = mock_stream_cm

        # Mock zipfile extraction — extractall creates a .gdb dir
        mock_zf = MagicMock()
        mock_zipfile.return_value.__enter__ = MagicMock(return_value=mock_zf)
        mock_zipfile.return_value.__exit__ = MagicMock(return_value=False)

        # Patch Path.rglob to return a fake .gdb path
        fake_gdb = Path("/tmp/fake/PADUS4_1.gdb")
        with patch("pricepoint.data.geospatial.pad_us.Path.rglob", return_value=[fake_gdb]):
            # Build a fake GeoDataFrame: 1 included, 1 excluded
            geom = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
            data = {
                "FID": [1, 2],
                "Unit_Nm": ["Good Park", "Closed Area"],
                "GIS_Acres": [100.0, 200.0],
                "Mang_Type": ["LOC", "FED"],
                "Mang_Name": ["City", "BLM"],
                "Des_Tp": ["LP", "NP"],
                "Pub_Access": ["OA", "XA"],  # 2nd row excluded
                "GAP_Sts": [2, 1],
                "d_State_Nm": ["North Carolina", "Montana"],
                "Category": ["Fee", "Fee"],
                "geometry": [geom, geom],
            }
            gdf = real_gpd.GeoDataFrame(pd.DataFrame(data), geometry="geometry")
            mock_gpd.read_file.return_value = gdf

            # Stale delete returns 0
            session.execute.return_value.rowcount = 0

            total = fetch_pad_us()

        assert total == 1  # Only the OA row
        assert mock_gpd.read_file.called

    @patch("pricepoint.data.geospatial.pad_us.gpd")
    @patch("pricepoint.data.geospatial.pad_us.zipfile.ZipFile")
    @patch("pricepoint.data.geospatial.pad_us.httpx")
    @patch("pricepoint.data.geospatial.pad_us.SessionLocal")
    @patch("pricepoint.data.geospatial.pad_us.get_settings")
    def test_stale_cleanup_after_upsert(
        self, mock_settings, mock_session_cls, mock_httpx, mock_zipfile, mock_gpd
    ):
        settings = MagicMock()
        settings.pad_us_download_url = "http://example.com/padus.zip"
        settings.pad_us_layer_name = "PADUS4_1Fee"
        mock_settings.return_value = settings

        session = MagicMock()
        mock_session_cls.return_value = session

        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/zip"}
        mock_resp.iter_bytes.return_value = [b"fake"]
        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__ = MagicMock(return_value=mock_resp)
        mock_stream_cm.__exit__ = MagicMock(return_value=False)
        mock_httpx.stream.return_value = mock_stream_cm

        mock_zf = MagicMock()
        mock_zipfile.return_value.__enter__ = MagicMock(return_value=mock_zf)
        mock_zipfile.return_value.__exit__ = MagicMock(return_value=False)

        fake_gdb = Path("/tmp/fake/PADUS4_1.gdb")
        with patch("pricepoint.data.geospatial.pad_us.Path.rglob", return_value=[fake_gdb]):
            geom = MultiPolygon([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
            data = {
                "FID": [1],
                "Unit_Nm": ["Park"],
                "GIS_Acres": [50.0],
                "Mang_Type": ["LOC"],
                "Mang_Name": ["City"],
                "Des_Tp": ["LP"],
                "Pub_Access": ["OA"],
                "GAP_Sts": [2],
                "d_State_Nm": ["NC"],
                "Category": ["Fee"],
                "geometry": [geom],
            }
            gdf = real_gpd.GeoDataFrame(pd.DataFrame(data), geometry="geometry")
            mock_gpd.read_file.return_value = gdf

            # Stale delete removes 5 rows
            session.execute.return_value.rowcount = 5

            fetch_pad_us()

        # Commit called at least once for upsert + stale cleanup
        assert session.commit.call_count >= 2


# ---------------------------------------------------------------------------
# verify_pad_us tests
# ---------------------------------------------------------------------------
class TestVerifyPadUs:
    @patch("pricepoint.data.geospatial.pad_us.SessionLocal")
    def test_returns_count_when_records_exist(self, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 42

        count = verify_pad_us()

        assert count == 42

    @patch("pricepoint.data.geospatial.pad_us.SessionLocal")
    def test_raises_when_empty(self, mock_session_cls):
        session = MagicMock()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records found"):
            verify_pad_us()
