"""Tests for transportation and utility collectors."""

from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.wake_transportation import (
    _map_highway,
    _map_major_road,
    _map_railroad,
    _map_utility_easement,
    fetch_highways,
    fetch_major_roads,
    fetch_railroads,
    fetch_utility_easements,
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


# -- Railroad -----------------------------------------------------------------


class TestMapRailroad:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 1,
                "BRANCH_OR": "CSX Main",
                "TRACK_TYPE": "Main",
                "TRACK_OWNER": "CSX",
                "Shape__Length": 12345.6,
            }
        )
        record = _map_railroad(feature)
        assert record.objectid == 1
        assert record.branch_or == "CSX Main"
        assert record.track_type == "Main"
        assert record.track_owner == "CSX"
        assert record.shape_length == 12345.6
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_railroad(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_railroad(feature)
        assert record.objectid is None
        assert record.branch_or is None


# -- Major Road ---------------------------------------------------------------


class TestMapMajorRoad:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 2,
                "STREET_NAME": "GLENWOOD",
                "STREET_TYPE": "AVE",
                "DIR_PREFIX": "N",
                "DIR_SUFFIX": "",
                "STATE_ROAD": "SR-1002",
                "CARTO_NAME": "Glenwood Ave",
                "CORPORATION": "Raleigh",
                "CLASS_NAME": "Major Arterial",
                "LABEL_NAME": "N Glenwood Ave",
            }
        )
        record = _map_major_road(feature)
        assert record.objectid == 2
        assert record.street_name == "GLENWOOD"
        assert record.street_type == "AVE"
        assert record.dir_prefix == "N"
        assert record.state_road == "SR-1002"
        assert record.carto_name == "Glenwood Ave"
        assert record.class_name == "Major Arterial"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_major_road(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_major_road(feature)
        assert record.objectid is None
        assert record.street_name is None


# -- Highway ------------------------------------------------------------------


class TestMapHighway:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 3,
                "STREET_NAME": "WADE",
                "STREET_TYPE": "AVE",
                "DIR_PREFIX": "",
                "DIR_SUFFIX": "",
                "FROM_LEFT": 100,
                "TO_LEFT": 200,
                "FROM_RIGHT": 101,
                "TO_RIGHT": 201,
                "STATE_ROAD": "US-1",
                "CARTO_NAME": "Wade Ave",
                "CORPORATION": "Raleigh",
                "CLASS_NAME": "Highway",
                "LABEL_NAME": "Wade Ave",
            }
        )
        record = _map_highway(feature)
        assert record.objectid == 3
        assert record.street_name == "WADE"
        assert record.from_left == 100
        assert record.to_left == 200
        assert record.from_right == 101
        assert record.to_right == 201
        assert record.state_road == "US-1"
        assert record.class_name == "Highway"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_highway(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_highway(feature)
        assert record.objectid is None
        assert record.street_name is None


# -- Utility Easement ---------------------------------------------------------


class TestMapUtilityEasement:
    def test_all_fields_mapped(self):
        feature = _make_line_feature(
            {
                "OBJECTID": 4,
                "LENGTH": 500.0,
                "FTR_CODE": "UE",
                "STATUS": "Active",
            }
        )
        record = _map_utility_easement(feature)
        assert record.objectid == 4
        assert record.length == 500.0
        assert record.ftr_code == "UE"
        assert record.status == "Active"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_line_feature()
        feature["geometry"] = None
        record = _map_utility_easement(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_utility_easement(feature)
        assert record.objectid is None
        assert record.length is None


# -- Fetch functions ----------------------------------------------------------


class TestFetchRailroads:
    @patch("pricepoint.data.geospatial.wake_transportation.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_transportation.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_railroads_base_url="http://test/0")
        fetch_railroads()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_railroads"


class TestFetchMajorRoads:
    @patch("pricepoint.data.geospatial.wake_transportation.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_transportation.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_major_roads_base_url="http://test/0")
        fetch_major_roads()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_major_roads"


class TestFetchHighways:
    @patch("pricepoint.data.geospatial.wake_transportation.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_transportation.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_highways_base_url="http://test/0")
        fetch_highways()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_highways"


class TestFetchUtilityEasements:
    @patch("pricepoint.data.geospatial.wake_transportation.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_transportation.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_utility_easements_base_url="http://test/0")
        fetch_utility_easements()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_utility_easements"
