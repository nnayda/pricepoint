"""Tests for USGS National Digital Trails collector."""

from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.trails import (
    _deduplicate_batch,
    _parse_trail,
    fetch_trails,
    verify_trails,
)

# -- Helpers ------------------------------------------------------------------

_SAMPLE_PATHS = [[[-78.6, 35.7], [-78.5, 35.8], [-78.4, 35.9]]]


def _make_trail_feature(attrs_override=None, paths=None):
    attrs = {
        "permanentidentifier": "abc-123",
        "name": "Test Trail",
        "trailtype": "Terra Trail",
        "lengthmiles": 2.5,
        "primarytrailmaintainer": "NPS",
        "nationaltraildesignation": None,
        "hikerpedestrian": "Yes",
        "bicycle": "No",
        "packsaddle": "No",
        "atv": "No",
        "motorcycle": "No",
        "ohvover50inches": "No",
        "snowshoe": "No",
        "crosscountryski": "No",
        "dogsled": "No",
        "snowmobile": "No",
        "nonmotorizedwatercraft": "No",
        "motorizedwatercraft": "No",
    }
    if attrs_override:
        attrs.update(attrs_override)
    return {
        "attributes": attrs,
        "geometry": {"paths": paths if paths is not None else _SAMPLE_PATHS},
    }


# -- _parse_trail tests -------------------------------------------------------


class TestParseTrail:
    def test_basic_extraction(self):
        feature = _make_trail_feature()
        result = _parse_trail(feature)
        assert result is not None
        assert result["permanentidentifier"] == "abc-123"
        assert result["name"] == "Test Trail"
        assert result["trail_type"] == "Terra Trail"
        assert result["length_miles"] == 2.5
        assert result["maintainer"] == "NPS"
        assert result["hiker_pedestrian"] == "Yes"
        assert result["bicycle"] == "No"
        assert result["geom"] is not None

    def test_missing_permanentidentifier_returns_none(self):
        feature = _make_trail_feature({"permanentidentifier": None})
        assert _parse_trail(feature) is None

    def test_empty_permanentidentifier_returns_none(self):
        feature = _make_trail_feature({"permanentidentifier": ""})
        assert _parse_trail(feature) is None

    def test_missing_geometry_returns_none(self):
        feature = _make_trail_feature()
        feature["geometry"] = None
        assert _parse_trail(feature) is None

    def test_empty_paths_returns_none(self):
        feature = _make_trail_feature(paths=[])
        assert _parse_trail(feature) is None

    def test_optional_fields_can_be_none(self):
        feature = _make_trail_feature(
            {
                "name": None,
                "lengthmiles": None,
                "primarytrailmaintainer": None,
            }
        )
        result = _parse_trail(feature)
        assert result is not None
        assert result["name"] is None
        assert result["length_miles"] is None
        assert result["maintainer"] is None


# -- _deduplicate_batch tests -------------------------------------------------


class TestDeduplicateBatch:
    def test_no_duplicates_unchanged(self):
        batch = [
            {"permanentidentifier": "a", "name": "Trail A"},
            {"permanentidentifier": "b", "name": "Trail B"},
        ]
        result = _deduplicate_batch(batch)
        assert len(result) == 2

    def test_duplicates_keep_longest(self):
        batch = [
            {"permanentidentifier": "a", "name": "Short", "length_miles": 1.0},
            {"permanentidentifier": "b", "name": "Trail B", "length_miles": 2.0},
            {"permanentidentifier": "a", "name": "Long", "length_miles": 3.0},
        ]
        result = _deduplicate_batch(batch)
        assert len(result) == 2
        names = {r["permanentidentifier"]: r["name"] for r in result}
        assert names["a"] == "Long"
        assert names["b"] == "Trail B"

    def test_duplicates_keep_first_when_equal_length(self):
        batch = [
            {"permanentidentifier": "a", "name": "First", "length_miles": 5.0},
            {"permanentidentifier": "a", "name": "Second", "length_miles": 5.0},
        ]
        result = _deduplicate_batch(batch)
        assert len(result) == 1
        assert result[0]["name"] == "First"

    def test_duplicates_handle_none_length(self):
        batch = [
            {"permanentidentifier": "a", "name": "No length", "length_miles": None},
            {"permanentidentifier": "a", "name": "Has length", "length_miles": 2.0},
        ]
        result = _deduplicate_batch(batch)
        assert len(result) == 1
        assert result[0]["name"] == "Has length"

    def test_duplicates_logged(self, caplog):
        batch = [
            {"permanentidentifier": "a", "name": "Long", "length_miles": 3.0},
            {"permanentidentifier": "a", "name": "Short", "length_miles": 1.0},
        ]
        with caplog.at_level("WARNING"):
            _deduplicate_batch(batch)
        assert "Dropping shorter duplicate trail: permanentidentifier=a" in caplog.text
        assert "name=Short" in caplog.text
        assert "length_miles=1.0" in caplog.text
        assert "keeping length_miles=3.0" in caplog.text

    def test_empty_batch(self):
        assert _deduplicate_batch([]) == []


# -- fetch_trails tests -------------------------------------------------------


class TestFetchTrails:
    @patch("pricepoint.data.geospatial.trails.SessionLocal")
    @patch("pricepoint.data.geospatial.trails.query_arcgis_page")
    @patch("pricepoint.data.geospatial.trails.get_settings")
    def test_fetches_and_upserts(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(trails_base_url="https://example.com/MapServer/37")
        mock_query.side_effect = [
            {"features": [_make_trail_feature()]},
            {"features": []},
        ]
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.rowcount = 0

        fetch_trails()

        assert mock_session.execute.called
        assert mock_session.commit.called

    @patch("pricepoint.data.geospatial.trails.SessionLocal")
    @patch("pricepoint.data.geospatial.trails.query_arcgis_page")
    @patch("pricepoint.data.geospatial.trails.get_settings")
    def test_skips_null_keys(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(trails_base_url="https://example.com/MapServer/37")
        feature_no_key = _make_trail_feature({"permanentidentifier": None})
        mock_query.side_effect = [
            {"features": [feature_no_key]},
            {"features": []},
        ]
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        fetch_trails()

        # No upsert should have been attempted (only stale cleanup skipped)
        # The session should still close cleanly
        mock_session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.trails.SessionLocal")
    @patch("pricepoint.data.geospatial.trails.query_arcgis_page")
    @patch("pricepoint.data.geospatial.trails.get_settings")
    def test_stale_cleanup(self, mock_settings, mock_query, mock_session_cls):
        mock_settings.return_value = MagicMock(trails_base_url="https://example.com/MapServer/37")
        mock_query.side_effect = [
            {"features": [_make_trail_feature()]},
            {"features": []},
        ]
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.rowcount = 3

        fetch_trails()

        # commit called at least twice: once for upsert batch, once for stale cleanup
        assert mock_session.commit.call_count >= 2


# -- verify_trails tests ------------------------------------------------------


class TestVerifyTrails:
    @patch("pricepoint.data.geospatial.trails.SessionLocal")
    def test_empty_table_raises(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 0

        try:
            verify_trails()
            raise AssertionError("Expected RuntimeError")
        except RuntimeError as exc:
            assert "No records" in str(exc)

    @patch("pricepoint.data.geospatial.trails.SessionLocal")
    def test_populated_table_returns(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = 42

        verify_trails()  # Should not raise
