"""Tests for Wake County amenity collectors (farmers markets, libraries, hospitals)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.wake_amenities import (
    _map_farmers_market,
    _map_hospital,
    _map_library,
    fetch_farmers_markets,
    fetch_hospitals,
    fetch_libraries,
)

# -- Helpers ------------------------------------------------------------------


def _make_point_feature(attrs_override=None, geometry=None):
    """Build a minimal ArcGIS point feature dict."""
    attrs = {"OBJECTID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    if geometry is None:
        geometry = {"x": -78.6, "y": 35.7}
    return {"attributes": attrs, "geometry": geometry}


# -- Farmers Market -----------------------------------------------------------


class TestMapFarmersMarket:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 1,
                "NAME": "State Farmers Market",
                "LOCATION": "1201 Agriculture St",
                "ORGANIZATI": "NCDA",
                "ACTIVEDAY": "Saturday",
                "MONTHS": "Apr-Nov",
                "HOURS": "8am-1pm",
                "WEBSITE": "http://example.com",
                "PHONE": "919-555-0100",
            }
        )
        record = _map_farmers_market(feature)
        assert record.objectid == 1
        assert record.name == "State Farmers Market"
        assert record.location_desc == "1201 Agriculture St"
        assert record.organization == "NCDA"
        assert record.active_day == "Saturday"
        assert record.months == "Apr-Nov"
        assert record.hours == "8am-1pm"
        assert record.website == "http://example.com"
        assert record.phone == "919-555-0100"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature(geometry=None)
        feature["geometry"] = None
        record = _map_farmers_market(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_farmers_market(feature)
        assert record.objectid is None
        assert record.name is None


# -- Library ------------------------------------------------------------------


class TestMapLibrary:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 2,
                "NAME": "Eva H. Perry Regional Library",
                "FAC_ADDRESS": "2100 Shepherd's Vineyard Dr",
                "CITY": "Apex",
                "CODE": "EP",
                "LABEL": "Eva Perry",
                "STATUS": "Open",
                "TYPE": "Regional",
                "M_T": "9am-9pm",
                "FRI": "9am-6pm",
                "SAT": "9am-5pm",
                "SUN": "1pm-5pm",
            }
        )
        record = _map_library(feature)
        assert record.objectid == 2
        assert record.name == "Eva H. Perry Regional Library"
        assert record.address == "2100 Shepherd's Vineyard Dr"
        assert record.city == "Apex"
        assert record.hours_mt == "9am-9pm"
        assert record.hours_sun == "1pm-5pm"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature(geometry=None)
        feature["geometry"] = None
        record = _map_library(feature)
        assert record.geom is None


# -- Hospital -----------------------------------------------------------------


class TestMapHospital:
    def test_all_fields_mapped(self):
        feature = _make_point_feature(
            {
                "OBJECTID": 3,
                "FACILITY": "WakeMed Raleigh Campus",
                "ADDRESS": "3000 New Bern Ave",
                "CITY": "Raleigh",
                "ACUTE_CARE": "Yes",
                "URL": "http://wakemed.org",
                "TELEPHONE": "919-350-8000",
                "GIS_EDT_DT": 1609459200000,
            }
        )
        record = _map_hospital(feature)
        assert record.objectid == 3
        assert record.facility == "WakeMed Raleigh Campus"
        assert record.address == "3000 New Bern Ave"
        assert record.city == "Raleigh"
        assert record.acute_care == "Yes"
        assert record.telephone == "919-350-8000"
        assert record.gis_edit_date == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_point_feature(geometry=None)
        feature["geometry"] = None
        record = _map_hospital(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_hospital(feature)
        assert record.objectid is None
        assert record.facility is None


# -- Fetch functions (integration with arcgis_client) -------------------------


class TestFetchFarmersMarkets:
    @patch("pricepoint.data.geospatial.wake_amenities.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_amenities.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_farmers_markets_base_url="http://test/0")
        fetch_farmers_markets()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_farmers_markets"


class TestFetchLibraries:
    @patch("pricepoint.data.geospatial.wake_amenities.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_amenities.get_settings")
    def test_calls_fetch_dataset_with_page_size(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_libraries_base_url="http://test/0")
        fetch_libraries()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["page_size"] == 1000


class TestFetchHospitals:
    @patch("pricepoint.data.geospatial.wake_amenities.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_amenities.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_hospitals_base_url="http://test/0")
        fetch_hospitals()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_hospitals"
