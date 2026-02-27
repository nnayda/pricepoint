"""Tests for the generic subdivision boundary collector."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.subdivisions import (
    FieldMap,
    SubdivisionSource,
    _build_multipolygon_wkb,
    _extract_field,
    _parse_arcgis_timestamp,
    _query_page,
    fetch_subdivisions,
    verify_subdivisions,
)

# -- Helpers ------------------------------------------------------------------

_WAKE_SOURCE = SubdivisionSource(
    county_fips="37183",
    base_url="https://maps.wake.gov/arcgis/rest/services/Planning/Subdivisions/MapServer/0",
    field_map=FieldMap(
        source_id="SNUMBER",
        name="NAME",
        acres="ACRES",
        lots="LOTS",
        density="DENSITY",
    ),
)

_DURHAM_SOURCE = SubdivisionSource(
    county_fips="37063",
    base_url="https://maps.durham.gov/arcgis/rest/services/Subdivisions/MapServer/0",
    field_map=FieldMap(
        source_id="OBJECTID",
        name="SUBDIV_NAME",
        acres=None,
        lots=None,
        density=None,
    ),
)


def _make_feature(source_id_field: str = "SNUMBER", source_id_val: str = "SN-001", **overrides):
    """Build a minimal ArcGIS feature dict for testing."""
    attrs = {
        source_id_field: source_id_val,
        "NAME": "SUNSET HILLS",
        "ACRES": 25.5,
        "LOTS": 42,
        "DENSITY": 1.65,
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

    def test_multiple_rings(self):
        rings = [
            [[-78.6, 35.7], [-78.6, 35.8], [-78.5, 35.8], [-78.5, 35.7], [-78.6, 35.7]],
            [[-79.0, 36.0], [-79.0, 36.1], [-78.9, 36.1], [-78.9, 36.0], [-79.0, 36.0]],
        ]
        result = _build_multipolygon_wkb(rings)
        assert result is not None

    def test_invalid_coords_returns_none(self):
        rings = [[[None, None]]]
        assert _build_multipolygon_wkb(rings) is None


# -- _extract_field -----------------------------------------------------------


class TestExtractField:
    def test_returns_value_when_mapped(self):
        assert _extract_field({"ACRES": 25.5}, "ACRES") == 25.5

    def test_returns_none_when_field_is_none(self):
        assert _extract_field({"ACRES": 25.5}, None) is None

    def test_returns_none_when_field_missing(self):
        assert _extract_field({}, "ACRES") is None


# -- FieldMap -----------------------------------------------------------------


class TestFieldMapping:
    def test_wake_field_map(self):
        attrs = {"SNUMBER": "SN-001", "NAME": "Test", "ACRES": 10.0, "LOTS": 5, "DENSITY": 2.0}
        fm = _WAKE_SOURCE.field_map
        assert attrs.get(fm.source_id) == "SN-001"
        assert attrs.get(fm.name) == "Test"
        assert _extract_field(attrs, fm.acres) == 10.0
        assert _extract_field(attrs, fm.lots) == 5
        assert _extract_field(attrs, fm.density) == 2.0

    def test_null_optional_fields(self):
        attrs = {"OBJECTID": 42, "SUBDIV_NAME": "Durham Sub"}
        fm = _DURHAM_SOURCE.field_map
        assert attrs.get(fm.source_id) == 42
        assert attrs.get(fm.name) == "Durham Sub"
        assert _extract_field(attrs, fm.acres) is None
        assert _extract_field(attrs, fm.lots) is None
        assert _extract_field(attrs, fm.density) is None


# -- _query_page --------------------------------------------------------------


class TestQueryPage:
    @patch("pricepoint.data.geospatial.subdivisions.httpx.get")
    def test_returns_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": [_make_feature()]}
        mock_get.return_value = mock_response

        result = _query_page("http://test.example.com/0", 0, 2000)
        assert len(result["features"]) == 1
        mock_get.assert_called_once()

    @patch("pricepoint.data.geospatial.subdivisions.httpx.get")
    def test_passes_pagination_params(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        _query_page("http://test.example.com/0", 100, 500)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["resultOffset"] == 100
        assert kwargs["params"]["resultRecordCount"] == 500
        assert kwargs["params"]["outSR"] == 4326


# -- fetch_subdivisions -------------------------------------------------------


class TestFetchSubdivisions:
    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.subdivisions._query_page")
    def test_single_source_happy_path(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        feature = _make_feature()
        mock_query.side_effect = [
            {"features": [feature]},
            {"features": []},
        ]

        stats = fetch_subdivisions(sources=[_WAKE_SOURCE])

        assert stats == {"37183": 1}
        # upsert execute called once per feature + once for stale delete
        assert session.execute.call_count >= 1
        session.commit.assert_called()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.subdivisions._query_page")
    def test_multiple_sources(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        wake_feature = _make_feature()
        durham_feature = _make_feature(
            source_id_field="OBJECTID",
            source_id_val="99",
            attributes={"SUBDIV_NAME": "Durham Place"},
        )

        # Each source returns < PAGE_SIZE features, so pagination stops after
        # one call per source (no second empty-page call needed).
        mock_query.side_effect = [
            {"features": [wake_feature]},
            {"features": [durham_feature]},
        ]

        stats = fetch_subdivisions(sources=[_WAKE_SOURCE, _DURHAM_SOURCE])

        assert stats["37183"] == 1
        assert stats["37063"] == 1

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.subdivisions._query_page")
    def test_empty_response(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.return_value = {"features": []}

        stats = fetch_subdivisions(sources=[_WAKE_SOURCE])

        assert stats == {"37183": 0}
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.subdivisions._query_page")
    def test_exception_triggers_rollback(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        mock_query.side_effect = RuntimeError("connection failed")

        with pytest.raises(RuntimeError, match="connection failed"):
            fetch_subdivisions(sources=[_WAKE_SOURCE])

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.subdivisions._query_page")
    def test_skips_features_without_source_id(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        # Feature with no SNUMBER key
        feature = _make_feature()
        del feature["attributes"]["SNUMBER"]

        mock_query.side_effect = [
            {"features": [feature]},
            {"features": []},
        ]

        stats = fetch_subdivisions(sources=[_WAKE_SOURCE])

        # Feature was skipped — no upsert execute except for stale cleanup
        assert stats == {"37183": 1}  # total counted by features, not inserts

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    @patch("pricepoint.data.geospatial.subdivisions._query_page")
    def test_multi_page_pagination(self, mock_query, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session

        page1 = [_make_feature(source_id_val=str(i)) for i in range(2000)]
        page2 = [_make_feature(source_id_val=str(i)) for i in range(2000, 2500)]
        mock_query.side_effect = [
            {"features": page1},
            {"features": page2},
        ]

        stats = fetch_subdivisions(sources=[_WAKE_SOURCE])

        assert stats["37183"] == 2500
        assert mock_query.call_count == 2


# -- verify_subdivisions ------------------------------------------------------


class TestVerifySubdivisions:
    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    def test_passes_with_enough_records(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 500

        verify_subdivisions(sources=[_WAKE_SOURCE])

        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    def test_raises_when_empty(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="expected >= 10"):
            verify_subdivisions(sources=[_WAKE_SOURCE])

    @patch("pricepoint.data.geospatial.subdivisions.SessionLocal")
    def test_raises_when_below_minimum(self, mock_session_cls):
        session = _mock_session()
        mock_session_cls.return_value = session
        session.execute.return_value.scalar.return_value = 5

        with pytest.raises(RuntimeError, match="expected >= 10"):
            verify_subdivisions(sources=[_WAKE_SOURCE])
