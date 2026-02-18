"""Tests for shared ArcGIS client utilities."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.arcgis_client import (
    build_multilinestring_wkb,
    build_multipolygon_wkb,
    build_point_wkb,
    fetch_arcgis_dataset,
    parse_arcgis_timestamp,
    query_arcgis_page,
    verify_arcgis_dataset,
)
from pricepoint.db.models import WakeUtilityEasement

# -- parse_arcgis_timestamp ---------------------------------------------------


class TestParseArcgisTimestamp:
    def test_valid_epoch_ms(self):
        result = parse_arcgis_timestamp(1609459200000)
        assert result == datetime(2021, 1, 1, tzinfo=UTC)

    def test_none_returns_none(self):
        assert parse_arcgis_timestamp(None) is None

    def test_zero_epoch(self):
        result = parse_arcgis_timestamp(0)
        assert result == datetime(1970, 1, 1, tzinfo=UTC)

    def test_invalid_value_returns_none(self):
        assert parse_arcgis_timestamp("not-a-number") is None


# -- build_point_wkb ---------------------------------------------------------


class TestBuildPointWkb:
    def test_valid_point(self):
        geom = {"x": -78.6, "y": 35.7}
        result = build_point_wkb(geom)
        assert result is not None

    def test_none_returns_none(self):
        assert build_point_wkb(None) is None

    def test_missing_x_returns_none(self):
        assert build_point_wkb({"y": 35.7}) is None

    def test_missing_y_returns_none(self):
        assert build_point_wkb({"x": -78.6}) is None

    def test_invalid_coords_returns_none(self):
        assert build_point_wkb({"x": "bad", "y": "bad"}) is None


# -- build_multipolygon_wkb --------------------------------------------------


class TestBuildMultipolygonWkb:
    def test_valid_rings(self):
        rings = [[[-78.6, 35.7], [-78.6, 35.8], [-78.5, 35.8], [-78.5, 35.7], [-78.6, 35.7]]]
        result = build_multipolygon_wkb(rings)
        assert result is not None

    def test_none_returns_none(self):
        assert build_multipolygon_wkb(None) is None

    def test_empty_list_returns_none(self):
        assert build_multipolygon_wkb([]) is None

    def test_multiple_rings(self):
        rings = [
            [[-78.6, 35.7], [-78.6, 35.8], [-78.5, 35.8], [-78.5, 35.7], [-78.6, 35.7]],
            [[-79.0, 36.0], [-79.0, 36.1], [-78.9, 36.1], [-78.9, 36.0], [-79.0, 36.0]],
        ]
        result = build_multipolygon_wkb(rings)
        assert result is not None

    def test_invalid_coords_returns_none(self):
        assert build_multipolygon_wkb([[[None, None]]]) is None


# -- build_multilinestring_wkb -----------------------------------------------


class TestBuildMultilinestringWkb:
    def test_valid_paths(self):
        paths = [[[-78.6, 35.7], [-78.5, 35.8], [-78.4, 35.9]]]
        result = build_multilinestring_wkb(paths)
        assert result is not None

    def test_none_returns_none(self):
        assert build_multilinestring_wkb(None) is None

    def test_empty_list_returns_none(self):
        assert build_multilinestring_wkb([]) is None

    def test_multiple_paths(self):
        paths = [
            [[-78.6, 35.7], [-78.5, 35.8]],
            [[-79.0, 36.0], [-78.9, 36.1]],
        ]
        result = build_multilinestring_wkb(paths)
        assert result is not None

    def test_invalid_coords_returns_none(self):
        assert build_multilinestring_wkb([[[None, None]]]) is None


# -- query_arcgis_page -------------------------------------------------------


class TestQueryArcgisPage:
    @patch("pricepoint.data.geospatial.arcgis_client.httpx.get")
    def test_returns_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": [{"attributes": {}}]}
        mock_get.return_value = mock_response

        result = query_arcgis_page("http://test.example.com/0", 0, 2000)
        assert len(result["features"]) == 1
        mock_get.assert_called_once()

    @patch("pricepoint.data.geospatial.arcgis_client.httpx.get")
    def test_passes_pagination_params(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        query_arcgis_page("http://test.example.com/0", 100, 500)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["resultOffset"] == 100
        assert kwargs["params"]["resultRecordCount"] == 500
        assert kwargs["params"]["outSR"] == 4326


# -- fetch_arcgis_dataset ----------------------------------------------------


def _mock_session():
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


class TestFetchArcgisDataset:
    @patch("pricepoint.data.geospatial.arcgis_client.SessionLocal")
    @patch("pricepoint.data.geospatial.arcgis_client.query_arcgis_page")
    def test_single_page(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.side_effect = [
            {"features": [{"attributes": {"OBJECTID": 1}}]},
            {"features": []},
        ]

        mapper = MagicMock(return_value=MagicMock())
        fetch_arcgis_dataset(
            "http://test/0", WakeUtilityEasement, mapper, "test_dataset"
        )

        session.add_all.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.arcgis_client.SessionLocal")
    @patch("pricepoint.data.geospatial.arcgis_client.query_arcgis_page")
    def test_multi_page(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        page1 = [{"attributes": {"OBJECTID": i}} for i in range(2000)]
        page2 = [{"attributes": {"OBJECTID": i}} for i in range(500)]
        mock_query.side_effect = [{"features": page1}, {"features": page2}]

        mapper = MagicMock(return_value=MagicMock())
        fetch_arcgis_dataset(
            "http://test/0", WakeUtilityEasement, mapper, "test_dataset"
        )

        assert session.add_all.call_count == 2

    @patch("pricepoint.data.geospatial.arcgis_client.SessionLocal")
    @patch("pricepoint.data.geospatial.arcgis_client.query_arcgis_page")
    def test_empty_response(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = {"features": []}

        mapper = MagicMock()
        fetch_arcgis_dataset(
            "http://test/0", WakeUtilityEasement, mapper, "test_dataset"
        )

        session.add_all.assert_not_called()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.arcgis_client.SessionLocal")
    @patch("pricepoint.data.geospatial.arcgis_client.query_arcgis_page")
    def test_exception_triggers_rollback(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.side_effect = RuntimeError("connection failed")

        with pytest.raises(RuntimeError, match="connection failed"):
            fetch_arcgis_dataset(
                "http://test/0", WakeUtilityEasement, MagicMock(), "test_dataset"
            )

        session.rollback.assert_called_once()
        session.close.assert_called_once()


# -- verify_arcgis_dataset ---------------------------------------------------


class TestVerifyArcgisDataset:
    @patch("pricepoint.data.geospatial.arcgis_client.SessionLocal")
    def test_passes_with_records(self, mock_session_cls):
        session = MagicMock()
        session.execute.return_value.scalar.return_value = 42
        mock_session_cls.return_value = session

        verify_arcgis_dataset(WakeUtilityEasement, "test_dataset")
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.arcgis_client.SessionLocal")
    def test_raises_on_empty(self, mock_session_cls):
        session = MagicMock()
        session.execute.return_value.scalar.return_value = 0
        mock_session_cls.return_value = session

        with pytest.raises(RuntimeError, match="No records found"):
            verify_arcgis_dataset(WakeUtilityEasement, "test_dataset")
