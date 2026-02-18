"""Tests for Wake County subdivision boundary collector."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.wake_subdivisions import (
    _build_multipolygon_wkb,
    _map_subdivision_record,
    _parse_arcgis_timestamp,
    _query_subdivisions_page,
    fetch_wake_subdivisions,
)

# -- Helpers ------------------------------------------------------------------


def _make_feature(**overrides):
    """Build a minimal ArcGIS feature dict for testing."""
    attrs = {
        "OBJECTID": 1,
        "NAME": "SUNSET HILLS",
        "SNUMBER": "SN-001",
        "ACCESS_RD": "Main St",
        "JURISDICTION": "Raleigh",
        "STATUS": "EXISTING",
        "ACRES": 25.5,
        "LOTS": 42,
        "DENSITY": 1.65,
        "MAPCLASS": 1,
        "ISCLUSTER": "N",
        "APPROVDATE": 1609459200000,  # 2021-01-01 UTC
        "APPLDATE": 1606780800000,  # 2020-12-01 UTC
        "last_edited_date": 1700000000000,
    }
    attrs.update(overrides.pop("attributes", {}))
    feature = {
        "attributes": attrs,
        "geometry": {
            "rings": [
                [
                    [-78.6, 35.7],
                    [-78.6, 35.8],
                    [-78.5, 35.8],
                    [-78.5, 35.7],
                    [-78.6, 35.7],
                ]
            ]
        },
    }
    feature.update(overrides)
    return feature


def _mock_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


# -- _parse_arcgis_timestamp --------------------------------------------------


class TestParseArcgisTimestamp:
    def test_valid_epoch_ms(self):
        result = _parse_arcgis_timestamp(1609459200000)
        assert result == datetime(2021, 1, 1, tzinfo=UTC)

    def test_none_returns_none(self):
        assert _parse_arcgis_timestamp(None) is None

    def test_zero_epoch(self):
        result = _parse_arcgis_timestamp(0)
        assert result == datetime(1970, 1, 1, tzinfo=UTC)

    def test_invalid_value_returns_none(self):
        assert _parse_arcgis_timestamp("not-a-number") is None


# -- _build_multipolygon_wkb -------------------------------------------------


class TestBuildMultipolygonWkb:
    def test_valid_rings(self):
        rings = [[[-78.6, 35.7], [-78.6, 35.8], [-78.5, 35.8], [-78.5, 35.7], [-78.6, 35.7]]]
        result = _build_multipolygon_wkb(rings)
        assert result is not None

    def test_none_returns_none(self):
        assert _build_multipolygon_wkb(None) is None

    def test_empty_list_returns_none(self):
        assert _build_multipolygon_wkb([]) is None

    def test_multiple_rings_create_multiple_polygons(self):
        rings = [
            [[-78.6, 35.7], [-78.6, 35.8], [-78.5, 35.8], [-78.5, 35.7], [-78.6, 35.7]],
            [[-79.0, 36.0], [-79.0, 36.1], [-78.9, 36.1], [-78.9, 36.0], [-79.0, 36.0]],
        ]
        result = _build_multipolygon_wkb(rings)
        assert result is not None

    def test_invalid_coords_returns_none(self):
        rings = [[[None, None]]]
        assert _build_multipolygon_wkb(rings) is None


# -- _map_subdivision_record --------------------------------------------------


class TestMapSubdivisionRecord:
    def test_all_fields_mapped(self):
        feature = _make_feature()
        record = _map_subdivision_record(feature)
        assert record.objectid == 1
        assert record.name == "SUNSET HILLS"
        assert record.snumber == "SN-001"
        assert record.access_rd == "Main St"
        assert record.jurisdiction == "Raleigh"
        assert record.status == "EXISTING"
        assert record.acres == 25.5
        assert record.lots == 42
        assert record.density == 1.65
        assert record.mapclass == 1
        assert record.iscluster == "N"
        assert record.approvdate == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_feature(geometry=None)
        record = _map_subdivision_record(feature)
        assert record.geom is None
        assert record.name == "SUNSET HILLS"

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_subdivision_record(feature)
        assert record.objectid is None
        assert record.name is None
        assert record.geom is None


# -- _query_subdivisions_page ------------------------------------------------


class TestQuerySubdivisionsPage:
    @patch("pricepoint.data.geospatial.wake_subdivisions.httpx.get")
    def test_returns_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": [_make_feature()]}
        mock_get.return_value = mock_response

        result = _query_subdivisions_page("http://test.example.com/0", 0, 2000)
        assert len(result["features"]) == 1
        mock_get.assert_called_once()

    @patch("pricepoint.data.geospatial.wake_subdivisions.httpx.get")
    def test_passes_pagination_params(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        _query_subdivisions_page("http://test.example.com/0", 100, 500)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["resultOffset"] == 100
        assert kwargs["params"]["resultRecordCount"] == 500
        assert kwargs["params"]["outSR"] == 4326


# -- fetch_wake_subdivisions -------------------------------------------------


class TestFetchWakeSubdivisions:
    @patch("pricepoint.data.geospatial.wake_subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.wake_subdivisions._query_subdivisions_page")
    @patch("pricepoint.data.geospatial.wake_subdivisions.get_settings")
    def test_single_page(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(
            wake_subdivisions_base_url="http://test.example.com/0"
        )
        mock_query.return_value = {"features": [_make_feature()]}
        session = _mock_session()
        mock_session_cls.return_value = session

        # First call returns 1 feature, second returns empty (end of pagination)
        mock_query.side_effect = [
            {"features": [_make_feature()]},
            {"features": []},
        ]

        fetch_wake_subdivisions()

        session.add_all.assert_called_once()
        assert len(session.add_all.call_args[0][0]) == 1
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.wake_subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.wake_subdivisions._query_subdivisions_page")
    @patch("pricepoint.data.geospatial.wake_subdivisions.get_settings")
    def test_multi_page(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(
            wake_subdivisions_base_url="http://test.example.com/0"
        )
        session = _mock_session()
        mock_session_cls.return_value = session

        # Page 1: full page (2000), page 2: partial (500) — stops pagination
        page1 = [_make_feature(attributes={"OBJECTID": i}) for i in range(2000)]
        page2 = [_make_feature(attributes={"OBJECTID": i}) for i in range(500)]
        mock_query.side_effect = [
            {"features": page1},
            {"features": page2},
        ]

        fetch_wake_subdivisions()

        assert session.add_all.call_count == 2
        assert len(session.add_all.call_args_list[0][0][0]) == 2000
        assert len(session.add_all.call_args_list[1][0][0]) == 500

    @patch("pricepoint.data.geospatial.wake_subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.wake_subdivisions._query_subdivisions_page")
    @patch("pricepoint.data.geospatial.wake_subdivisions.get_settings")
    def test_empty_response(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(
            wake_subdivisions_base_url="http://test.example.com/0"
        )
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = {"features": []}

        fetch_wake_subdivisions()

        session.add_all.assert_not_called()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.wake_subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.wake_subdivisions._query_subdivisions_page")
    @patch("pricepoint.data.geospatial.wake_subdivisions.get_settings")
    def test_exception_triggers_rollback(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(
            wake_subdivisions_base_url="http://test.example.com/0"
        )
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.side_effect = RuntimeError("connection failed")

        with pytest.raises(RuntimeError, match="connection failed"):
            fetch_wake_subdivisions()

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.wake_subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.wake_subdivisions._query_subdivisions_page")
    @patch("pricepoint.data.geospatial.wake_subdivisions.get_settings")
    def test_deletes_existing_before_load(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(
            wake_subdivisions_base_url="http://test.example.com/0"
        )
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = {"features": []}

        fetch_wake_subdivisions()

        # First call should be delete, then commit
        session.execute.assert_called_once()
        assert session.commit.call_count >= 1
