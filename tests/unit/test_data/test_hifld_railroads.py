"""Tests for HIFLD railroad collector."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.hifld_railroads import (
    _fips_to_state_abbr,
    _parse_feature,
    fetch_railroads,
    verify_railroads,
)

# -- Sample data ---------------------------------------------------------------

_FULL_FEATURE: dict = {
    "type": "Feature",
    "properties": {
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
    "geometry": {
        "type": "MultiLineString",
        "coordinates": [[[-78.6, 35.8], [-78.7, 35.9]]],
    },
}

_LINESTRING_FEATURE: dict = {
    "type": "Feature",
    "properties": {
        "FRAARCID": 789012,
        "RROWNER1": "Norfolk Southern",
        "RROWNER2": None,
        "RROWNER3": None,
        "STATEAB": "NC",
        "CNTYFIPS": "37183",
        "SUBDIVISIO": "Branch Line",
        "BRANCH": "Durham",
        "PASSNGR": "Y",
        "TRACKS": 1,
        "MILES": 5.3,
        "NET": "M",
    },
    "geometry": {
        "type": "LineString",
        "coordinates": [[-78.9, 35.7], [-79.0, 35.8]],
    },
}

_NO_GEOM_FEATURE: dict = {
    "type": "Feature",
    "properties": {
        "FRAARCID": 999999,
        "RROWNER1": "Amtrak",
        "STATEAB": "NC",
    },
    "geometry": None,
}

_NO_FRAARCID_FEATURE: dict = {
    "type": "Feature",
    "properties": {
        "RROWNER1": "Unknown",
    },
    "geometry": {
        "type": "LineString",
        "coordinates": [[-78.6, 35.8], [-78.7, 35.9]],
    },
}


# -- _fips_to_state_abbr -------------------------------------------------------


class TestFipsToStateAbbr:
    def test_known_fips(self):
        assert _fips_to_state_abbr("37") == "NC"
        assert _fips_to_state_abbr("06") == "CA"

    def test_unknown_fips_raises(self):
        with pytest.raises(ValueError, match="Unknown state FIPS"):
            _fips_to_state_abbr("99")


# -- _parse_feature ------------------------------------------------------------


class TestParseFeature:
    def test_full_feature(self):
        result = _parse_feature(_FULL_FEATURE)
        assert result is not None
        assert result["fraarcid"] == 123456
        assert result["rrowner1"] == "CSX Transportation"
        assert result["stateab"] == "NC"
        assert result["cntyfips"] == "37183"
        assert result["subdivision"] == "Main Line"
        assert result["passngr"] == "N"
        assert result["tracks"] == 2
        assert result["miles"] == 12.5
        assert result["net"] == "M"
        assert result["geom"] is not None

    def test_linestring_promoted_to_multi(self):
        result = _parse_feature(_LINESTRING_FEATURE)
        assert result is not None
        assert result["geom"] is not None
        assert result["fraarcid"] == 789012

    def test_no_geometry(self):
        result = _parse_feature(_NO_GEOM_FEATURE)
        assert result is not None
        assert result["geom"] is None
        assert result["fraarcid"] == 999999

    def test_no_fraarcid_returns_none(self):
        result = _parse_feature(_NO_FRAARCID_FEATURE)
        assert result is None

    def test_null_tracks_and_miles(self):
        feature = {
            "type": "Feature",
            "properties": {"FRAARCID": 111, "TRACKS": None, "MILES": None},
            "geometry": None,
        }
        result = _parse_feature(feature)
        assert result is not None
        assert result["tracks"] is None
        assert result["miles"] is None


# -- fetch_railroads -----------------------------------------------------------


class TestFetchRailroads:
    @patch("pricepoint.data.geospatial.hifld_railroads.SessionLocal")
    @patch("pricepoint.data.geospatial.hifld_railroads._fetch_page")
    @patch("pricepoint.data.geospatial.hifld_railroads.get_settings")
    def test_fetch_single_page(self, mock_settings, mock_fetch_page, mock_session_cls):
        settings = MagicMock()
        settings.hifld_railroads_base_url = "https://example.com/FeatureServer/0"
        settings.tiger_state_fips = "37"
        mock_settings.return_value = settings

        mock_fetch_page.side_effect = [[_FULL_FEATURE], []]

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        count = fetch_railroads()
        assert count == 1
        mock_session.execute.assert_called()
        mock_session.commit.assert_called()
        mock_session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.hifld_railroads.SessionLocal")
    @patch("pricepoint.data.geospatial.hifld_railroads._fetch_page")
    @patch("pricepoint.data.geospatial.hifld_railroads.get_settings")
    def test_fetch_empty_response(self, mock_settings, mock_fetch_page, mock_session_cls):
        settings = MagicMock()
        settings.hifld_railroads_base_url = "https://example.com/FeatureServer/0"
        settings.tiger_state_fips = "37"
        mock_settings.return_value = settings

        mock_fetch_page.return_value = []

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        count = fetch_railroads()
        assert count == 0
        mock_session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.hifld_railroads.SessionLocal")
    @patch("pricepoint.data.geospatial.hifld_railroads._fetch_page")
    @patch("pricepoint.data.geospatial.hifld_railroads.get_settings")
    def test_fetch_rollback_on_error(self, mock_settings, mock_fetch_page, mock_session_cls):
        settings = MagicMock()
        settings.hifld_railroads_base_url = "https://example.com/FeatureServer/0"
        settings.tiger_state_fips = "37"
        mock_settings.return_value = settings

        mock_fetch_page.side_effect = RuntimeError("API error")

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        with pytest.raises(RuntimeError, match="API error"):
            fetch_railroads()
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


# -- verify_railroads ----------------------------------------------------------


class TestVerifyRailroads:
    @patch("pricepoint.data.geospatial.hifld_railroads.SessionLocal")
    def test_verify_with_records(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 42

        result = verify_railroads()
        assert result == 42

    @patch("pricepoint.data.geospatial.hifld_railroads.SessionLocal")
    def test_verify_empty_raises(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records found"):
            verify_railroads()
