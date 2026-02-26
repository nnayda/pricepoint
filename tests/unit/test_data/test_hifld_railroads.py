"""Tests for HIFLD railroad collector."""

from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.hifld_railroads import (
    _map_railroad,
    fetch_railroads,
    verify_railroads,
)

# -- Sample data ---------------------------------------------------------------

_SAMPLE_PATHS = [[[-78.6, 35.8], [-78.7, 35.9]]]

_FULL_FEATURE: dict = {
    "attributes": {
        "FRAARCID": 123456,
        "RROWNER1": "CSX Transportation",
        "RROWNER2": None,
        "RROWNER3": None,
        "STATEAB": "NC",
        "CNTYFIPS": "37183",
        "SUBDIVISIO": "Main Line",
        "BRANCH": None,
        "PASSNGR": "N",
        "TRACKS": 2,
        "MILES": 12.5,
        "NET": "M",
    },
    "geometry": {"paths": _SAMPLE_PATHS},
}


def _make_feature(attrs_override=None, paths=None):
    attrs = {"FRAARCID": 1}
    if attrs_override:
        attrs.update(attrs_override)
    return {
        "attributes": attrs,
        "geometry": {"paths": paths if paths is not None else _SAMPLE_PATHS},
    }


# -- _map_railroad -------------------------------------------------------------


class TestMapRailroad:
    def test_all_fields_mapped(self):
        record = _map_railroad(_FULL_FEATURE)
        assert record.fraarcid == 123456
        assert record.rrowner1 == "CSX Transportation"
        assert record.rrowner2 is None
        assert record.rrowner3 is None
        assert record.stateab == "NC"
        assert record.cntyfips == "37183"
        assert record.subdivision == "Main Line"
        assert record.branch is None
        assert record.passngr == "N"
        assert record.tracks == 2
        assert record.miles == 12.5
        assert record.net == "M"
        assert record.geom is not None

    def test_none_geometry(self):
        feature = _make_feature({"FRAARCID": 999})
        feature["geometry"] = None
        record = _map_railroad(feature)
        assert record.geom is None
        assert record.fraarcid == 999

    def test_missing_attributes(self):
        feature = {"attributes": {}, "geometry": None}
        record = _map_railroad(feature)
        assert record.fraarcid is None
        assert record.rrowner1 is None

    def test_null_tracks_and_miles(self):
        feature = _make_feature({"FRAARCID": 111, "TRACKS": None, "MILES": None})
        record = _map_railroad(feature)
        assert record.tracks is None
        assert record.miles is None

    def test_subdivision_fallback(self):
        """SUBDIVISIO is preferred, but SUBDIVISION is used as fallback."""
        feature = _make_feature({"SUBDIVISIO": None, "SUBDIVISION": "Fallback Sub"})
        record = _map_railroad(feature)
        assert record.subdivision == "Fallback Sub"


# -- fetch_railroads -----------------------------------------------------------


class TestFetchRailroads:
    @patch("pricepoint.data.geospatial.hifld_railroads.fetch_arcgis_dataset")
    @patch("pricepoint.data.geospatial.hifld_railroads.get_settings")
    def test_calls_fetch_dataset(self, mock_settings, mock_fetch):
        mock_settings.return_value = MagicMock(
            hifld_railroads_base_url="http://test/FeatureServer/0"
        )
        fetch_railroads()
        mock_fetch.assert_called_once()
        _, kwargs = mock_fetch.call_args
        assert kwargs["dataset_name"] == "railroads"


# -- verify_railroads ----------------------------------------------------------


class TestVerifyRailroads:
    @patch("pricepoint.data.geospatial.hifld_railroads.verify_arcgis_dataset")
    def test_calls_verify_dataset(self, mock_verify):
        verify_railroads()
        mock_verify.assert_called_once()
