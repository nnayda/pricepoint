"""Tests for park collectors (Wake, Raleigh, Cary)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.wake_parks import (
    _map_cary_park,
    _map_raleigh_park,
    _map_wake_park,
    fetch_cary_parks,
    fetch_raleigh_parks,
    fetch_wake_parks,
)

# -- Helpers ------------------------------------------------------------------

_SAMPLE_RINGS = [[[-78.6, 35.7], [-78.6, 35.8], [-78.5, 35.8], [-78.5, 35.7], [-78.6, 35.7]]]


def _make_polygon_feature(attrs_override=None, rings=None):
    attrs = {"OBJECTID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    return {
        "attributes": attrs,
        "geometry": {"rings": rings if rings is not None else _SAMPLE_RINGS},
    }


def _make_point_feature(attrs_override=None):
    attrs = {"OBJECTID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    return {"attributes": attrs, "geometry": {"x": -78.6, "y": 35.7}}


# -- Wake Parks ---------------------------------------------------------------


class TestMapWakePark:
    def test_all_fields_mapped(self):
        feature = _make_polygon_feature(
            {
                "OBJECTID": 1,
                "NAME": "Umstead State Park",
                "ACRES": 5579.0,
                "OWNER": "State of NC",
                "JURISDICTION": "Wake",
                "PARK_TYPE": "State Park",
                "MANAGER": "NC Parks",
                "COMMENTS": "Major park",
                "CORRIDOR": "Crabtree",
                "OS_NUMBER": "OS-001",
                "created_date": 1609459200000,
                "last_edited_date": 1700000000000,
            }
        )
        record = _map_wake_park(feature)
        assert record.objectid == 1
        assert record.name == "Umstead State Park"
        assert record.acres == 5579.0
        assert record.owner == "State of NC"
        assert record.park_type == "State Park"
        assert record.created_date == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_polygon_feature()
        feature["geometry"] = None
        record = _map_wake_park(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_wake_park(feature)
        assert record.objectid is None
        assert record.name is None


# -- Raleigh Parks ------------------------------------------------------------


class TestMapRaleighPark:
    def test_all_fields_mapped(self):
        feature = _make_polygon_feature(
            {
                "OBJECTID": 2,
                "NAME": "Pullen Park",
                "PARK_TYPE": "Community",
                "DEVELOPED": "Yes",
                "MAP_ACRES": 66.3,
                "ADDRESS": "520 Ashe Ave",
                "ZIP_CODE": "27606",
                "PARK_ID": "P-042",
                "INITIAL_ACQUISITION_DATE": 1609459200000,
            }
        )
        record = _map_raleigh_park(feature)
        assert record.objectid == 2
        assert record.name == "Pullen Park"
        assert record.map_acres == 66.3
        assert record.zip_code == "27606"
        assert record.initial_acquisition_date == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_polygon_feature()
        feature["geometry"] = None
        record = _map_raleigh_park(feature)
        assert record.geom is None


# -- Cary Parks ---------------------------------------------------------------


class TestMapCaryPark:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 3,
                "NAME": "Fred G. Bond Metro Park",
                "FACILITY_ID": "F-001",
                "ADDRESS": "801 High House Rd",
                "PARK_AREA": 310.0,
                "PARK_URL": "http://example.com",
                "NUM_PARKING": 200,
                "RESTROOM": "Yes",
                "ADA_COMPLIANT": "Yes",
                "CAMPING": "No",
                "SWIMMING": "Yes",
                "HIKING": "Yes",
                "FISHING": "Yes",
                "PICNIC": "Yes",
                "BOATING": "Yes",
                "ROAD_CYCLE": "No",
                "MTB_CYCLE": "No",
                "PLAYGROUND": "Yes",
                "GOLF": "No",
                "SOCCER": "Yes",
                "BASEBALL": "Yes",
                "BASKETBALL": "Yes",
                "SKATEPARK": "No",
                "TENNIS_COURT": "Yes",
                "VOLLEYBALL": "Yes",
                "FITNESS_TRAIL": "Yes",
                "NATURE_TRAIL": "Yes",
                "TRAILHEAD": "Yes",
                "OPEN_SPACE": "Yes",
                "LAKE": "Yes",
                "AMPHITHEATER": "Yes",
                "DOG_PARK": "Yes",
                "DISC_GOLF": "No",
                "CLIMBING_ROCKS": "No",
                "CLIMBING_ROPES": "No",
                "BATTING_CAGES": "No",
            }
        )
        record = _map_cary_park(feature)
        assert record.objectid == 3
        assert record.name == "Fred G. Bond Metro Park"
        assert record.facility_id == "F-001"
        assert record.park_area == 310.0
        assert record.num_parking == 200
        assert record.swimming == "Yes"
        assert record.hiking == "Yes"
        assert record.dog_park == "Yes"
        assert record.batting_cages == "No"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature()
        feature["geometry"] = None
        record = _map_cary_park(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_cary_park(feature)
        assert record.objectid is None
        assert record.name is None


# -- Fetch functions ----------------------------------------------------------


class TestFetchWakeParks:
    @patch("pricepoint.data.geospatial.wake_parks.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_parks.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_parks_base_url="http://test/0")
        fetch_wake_parks()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_parks"


class TestFetchRaleighParks:
    @patch("pricepoint.data.geospatial.wake_parks.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_parks.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(raleigh_parks_base_url="http://test/0")
        fetch_raleigh_parks()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "raleigh_parks"


class TestFetchCaryParks:
    @patch("pricepoint.data.geospatial.wake_parks.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_parks.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(cary_parks_base_url="http://test/0")
        fetch_cary_parks()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "cary_parks"
