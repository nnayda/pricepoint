"""Tests for Wake County open space collector."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.wake_open_space import (
    _map_wake_open_space,
    fetch_wake_open_space,
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


# -- Mapping ------------------------------------------------------------------


class TestMapWakeOpenSpace:
    def test_all_fields_mapped(self):
        feature = _make_polygon_feature(
            {
                "OBJECTID": 1,
                "NAME": "Umstead State Park",
                "ACRES": 5579.0,
                "OWNER": "State of NC",
                "JURISDICTION": "Wake",
                "TYPE": "State Park",
                "MANAGER": "NC Parks",
                "COMMENTS": "Major park",
                "BLDGCODE": "B-100",
                "CORRIDOR": "Crabtree",
                "OS_NUMBER": "OS-001",
                "created_date": 1609459200000,
                "last_edited_date": 1700000000000,
            }
        )
        record = _map_wake_open_space(feature)
        assert record.objectid == 1
        assert record.name == "Umstead State Park"
        assert record.acres == 5579.0
        assert record.owner == "State of NC"
        assert record.jurisdiction == "Wake"
        assert record.type == "State Park"
        assert record.manager == "NC Parks"
        assert record.comments == "Major park"
        assert record.bldgcode == "B-100"
        assert record.corridor == "Crabtree"
        assert record.os_number == "OS-001"
        assert record.created_date == datetime(2021, 1, 1, tzinfo=UTC)
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_polygon_feature()
        feature["geometry"] = None
        record = _map_wake_open_space(feature)
        assert record.geom is None

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_wake_open_space(feature)
        assert record.objectid is None
        assert record.name is None
        assert record.type is None
        assert record.bldgcode is None


# -- Fetch function -----------------------------------------------------------


class TestFetchWakeOpenSpace:
    @patch("pricepoint.data.geospatial.wake_open_space.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.wake_open_space.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(wake_open_space_base_url="http://test/0")
        fetch_wake_open_space()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "wake_open_space"
