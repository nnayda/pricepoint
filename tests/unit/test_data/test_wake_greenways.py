"""Tests for greenway collectors (Wake, Raleigh, Cary)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.wake_greenways import (
    _map_cary_greenway,
    _map_raleigh_greenway,
    _map_wake_greenway,
    fetch_cary_greenways,
    fetch_raleigh_greenways,
    fetch_wake_greenways,
)

# -- Helpers ------------------------------------------------------------------

_SAMPLE_PATHS = [[[-78.6, 35.7], [-78.5, 35.8], [-78.4, 35.9]]]


def _make_line_feature(attrs_override=None, paths=None):
    attrs = {"OBJECTID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    return {
        "attributes": attrs,
        "geometry": {"paths": paths if paths is not None else _SAMPLE_PATHS},
    }


# -- Wake Greenways -----------------------------------------------------------


class TestMapWakeGreenway:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 1,
                "TRAIL_NAME": "Neuse River Trail",
                "CORRIDOR_NAME": "Neuse River",
                "OWNER": "Wake County",
                "TRAIL_STATUS": "Open",
                "TRAIL_SURFACE": "Asphalt",
                "TRAIL_CLASS": "Greenway",
                "LENGTH": 27.5,
                "WIDTH": 10.0,
                "OPEN_DATE": 1609459200000,
                "PUBLIC_ACCESS": "Yes",
                "ACCESSIBILITY_STATUS": "Accessible",
                "TRAIL_CONDITION": "Good",
                "SLOPE": "Flat",
                "SUBSEGMENT_NAME": "Section A",
            }
        )
        record = _map_wake_greenway(feature)
        assert record.objectid == 1
        assert record.trail_name == "Neuse River Trail"
        assert record.corridor_name == "Neuse River"
        assert record.owner == "Wake County"
        assert record.trail_surface == "Asphalt"
        assert record.length == 27.5
        assert record.width == 10.0
        assert record.open_date == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.trail_condition == "Good"
        assert record.slope == "Flat"
        assert record.subsegment_name == "Section A"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_wake_greenway(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_wake_greenway(feature)
        assert record.objectid is None
        assert record.trail_name is None


# -- Raleigh Greenways --------------------------------------------------------


class TestMapRaleighGreenway:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 2,
                "TRAIL_NAME": "Walnut Creek Trail",
                "TYPE": "Paved",
                "LOCATION": "South Raleigh",
                "STATUS": "Open",
                "MATERIAL": "Asphalt",
                "MAP_MILES": 3.5,
                "WIDTH_FT": 10.0,
                "OWNER": "City of Raleigh",
                "ADA": "Yes",
                "GWSTATUS": "Existing",
            }
        )
        record = _map_raleigh_greenway(feature)
        assert record.objectid == 2
        assert record.trail_name == "Walnut Creek Trail"
        assert record.greenway_type == "Paved"
        assert record.map_miles == 3.5
        assert record.width_ft == 10.0
        assert record.ada == "Yes"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_raleigh_greenway(feature)
        assert record.geom is None


# -- Cary Greenways -----------------------------------------------------------


class TestMapCaryGreenway:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 3,
                "NAME": "Black Creek Greenway",
                "SEGMENT": "Phase 2",
                "LENGTH": 2.1,
                "WIDTH": 10.0,
                "TRAILTYPE": "Greenway",
                "SURFTYPE": "Asphalt",
                "STATUS": "Open",
                "INSTALLDATE": 1609459200000,
                "OPENTOPUBLIC": "Yes",
                "PROJNAME": "Western Cary Greenways",
                "PROJNUM": "P-2024-001",
                "NOTES": "Phase 2 extension",
                "LOOPTRAIL": "Yes",
                "LOOPNAME": "Black Creek Loop",
                "CARYGWAYMICOUNT": 1.8,
            }
        )
        record = _map_cary_greenway(feature)
        assert record.objectid == 3
        assert record.name == "Black Creek Greenway"
        assert record.segment == "Phase 2"
        assert record.length == 2.1
        assert record.surface_type == "Asphalt"
        assert record.install_date == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.open_to_public == "Yes"
        assert record.project_name == "Western Cary Greenways"
        assert record.project_number == "P-2024-001"
        assert record.notes == "Phase 2 extension"
        assert record.loop_trail == "Yes"
        assert record.loop_name == "Black Creek Loop"
        assert record.official_cary_greenway_miles == 1.8
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_cary_greenway(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_cary_greenway(feature)
        assert record.objectid is None
        assert record.name is None


# -- Fetch functions ----------------------------------------------------------


class TestFetchWakeGreenways:
    @patch("pricepoint.data.geospatial.wake_greenways.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_greenways.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_greenways_base_url="http://test/0")
        fetch_wake_greenways()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_greenways"


class TestFetchRaleighGreenways:
    @patch("pricepoint.data.geospatial.wake_greenways.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_greenways.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(raleigh_greenways_base_url="http://test/0")
        fetch_raleigh_greenways()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "raleigh_greenways"


class TestFetchCaryGreenways:
    @patch("pricepoint.data.geospatial.wake_greenways.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_greenways.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(cary_greenways_base_url="http://test/0")
        fetch_cary_greenways()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "cary_greenways"
