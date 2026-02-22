"""Tests for the school enrichment module."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.housing.school_enrichment import (
    _normalize_school_name,
    geocode_school_nominatim,
    get_osrm_route,
    get_travel_times,
    get_travel_times_batch,
    match_nces_school,
)


# ---------------------------------------------------------------------------
# TestNormalizeSchoolName
# ---------------------------------------------------------------------------
class TestNormalizeSchoolName:
    def test_strips_elementary_school(self):
        assert _normalize_school_name("Mills Park Elementary School") == "mills park"

    def test_strips_middle_school(self):
        assert _normalize_school_name("Davis Drive Middle School") == "davis drive"

    def test_strips_high_school(self):
        assert _normalize_school_name("Green Hope High School") == "green hope"

    def test_strips_elementary_only(self):
        assert _normalize_school_name("Northwoods Elementary") == "northwoods"

    def test_strips_school_suffix(self):
        assert _normalize_school_name("Cary Academy School") == "cary academy"

    def test_lowercase(self):
        assert _normalize_school_name("MILLS PARK") == "mills park"

    def test_strips_whitespace(self):
        assert _normalize_school_name("  Mills Park  ") == "mills park"

    def test_no_suffix_match(self):
        assert _normalize_school_name("Cary Institute") == "cary institute"

    def test_strips_magnet(self):
        assert _normalize_school_name("Downtown Magnet") == "downtown"

    def test_strips_academy(self):
        assert _normalize_school_name("Leadership Academy") == "leadership"


# ---------------------------------------------------------------------------
# TestMatchNcesSchool
# ---------------------------------------------------------------------------
class TestMatchNcesSchool:
    def _make_nces(self, name="Test Elementary School", nces_id="001"):
        mock = MagicMock()
        mock.name = name
        mock.nces_id = nces_id
        mock.street = "100 Main St"
        mock.city = "Cary"
        mock.state = "NC"
        mock.zip_code = "27513"
        mock.location = MagicMock()
        return mock

    def test_finds_matching_school(self):
        session = MagicMock()
        candidate = self._make_nces(name="Mills Park Elementary School")
        session.execute.return_value.scalars.return_value.all.return_value = [candidate]

        result = match_nces_school(session, "Mills Park Elementary", 35.79, -78.78)
        assert result is not None
        assert result.nces_id == "001"

    def test_no_candidates_returns_none(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []

        result = match_nces_school(session, "Unknown School", 35.79, -78.78)
        assert result is None

    def test_below_threshold_returns_none(self):
        session = MagicMock()
        candidate = self._make_nces(name="Completely Different Name")
        session.execute.return_value.scalars.return_value.all.return_value = [candidate]

        result = match_nces_school(session, "XYZ Academy", 35.79, -78.78)
        assert result is None

    def test_best_match_selected(self):
        session = MagicMock()
        c1 = self._make_nces(name="Mills Park Elementary School", nces_id="001")
        c2 = self._make_nces(name="Mills Park Middle School", nces_id="002")
        session.execute.return_value.scalars.return_value.all.return_value = [c1, c2]

        result = match_nces_school(session, "Mills Park Elementary", 35.79, -78.78)
        assert result is not None
        assert result.nces_id == "001"


# ---------------------------------------------------------------------------
# TestGeocodeSchoolNominatim
# ---------------------------------------------------------------------------
class TestGeocodeSchoolNominatim:
    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_returns_result(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                "lat": "35.79",
                "lon": "-78.78",
                "display_name": "Mills Park Elementary, Cary, NC",
            }
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = geocode_school_nominatim("Mills Park Elementary", 35.79, -78.78)
        assert result is not None
        assert result["lat"] == pytest.approx(35.79)
        assert result["lon"] == pytest.approx(-78.78)
        assert "Mills Park" in result["address"]

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_no_results(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = geocode_school_nominatim("Nonexistent School", 35.79, -78.78)
        assert result is None

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_viewbox_passed(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geocode_school_nominatim("Test School", 35.79, -78.78)
        call_args = mock_get.call_args
        assert "viewbox" in call_args[1]["params"]

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_error_returns_none(self, mock_get, mock_sleep):
        mock_get.side_effect = Exception("Network error")
        result = geocode_school_nominatim("Test School", 35.79, -78.78)
        assert result is None

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_respects_rate_limit(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        geocode_school_nominatim("Test School", 35.79, -78.78)
        mock_sleep.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# TestGetOsrmRoute
# ---------------------------------------------------------------------------
class TestGetOsrmRoute:
    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_car_route(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": "Ok",
            "routes": [{"duration": 300.0, "distance": 5000.0}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_osrm_route(35.79, -78.78, 35.80, -78.79, profile="car")
        assert result is not None
        assert result["duration_minutes"] == pytest.approx(5.0)
        assert result["distance_miles"] == pytest.approx(3.1, abs=0.1)

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_foot_route(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": "Ok",
            "routes": [{"duration": 1200.0, "distance": 5000.0}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_osrm_route(35.79, -78.78, 35.80, -78.79, profile="foot")
        assert result is not None
        assert result["duration_minutes"] == pytest.approx(20.0)

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_error_returns_none(self, mock_get, mock_sleep):
        mock_get.side_effect = Exception("OSRM error")
        result = get_osrm_route(35.79, -78.78, 35.80, -78.79)
        assert result is None

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_non_ok_code(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": "NoRoute", "routes": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_osrm_route(35.79, -78.78, 35.80, -78.79)
        assert result is None


# ---------------------------------------------------------------------------
# TestGetTravelTimes
# ---------------------------------------------------------------------------
class TestGetTravelTimes:
    @patch("pricepoint.data.housing.school_enrichment.get_osrm_route")
    def test_both_modes(self, mock_route):
        mock_route.side_effect = [
            {"duration_minutes": 5.0, "distance_miles": 3.0},  # car
            {"duration_minutes": 20.0, "distance_miles": 3.0},  # foot
        ]

        result = get_travel_times(35.79, -78.78, 35.80, -78.79)
        assert result["drive_minutes"] == 5
        assert result["walk_minutes"] == 20

    @patch("pricepoint.data.housing.school_enrichment.get_osrm_route")
    def test_car_only(self, mock_route):
        mock_route.side_effect = [
            {"duration_minutes": 5.0, "distance_miles": 3.0},  # car
            None,  # foot failed
        ]

        result = get_travel_times(35.79, -78.78, 35.80, -78.79)
        assert result["drive_minutes"] == 5
        assert result["walk_minutes"] is None

    @patch("pricepoint.data.housing.school_enrichment.get_osrm_route")
    def test_both_fail(self, mock_route):
        mock_route.return_value = None

        result = get_travel_times(35.79, -78.78, 35.80, -78.79)
        assert result["drive_minutes"] is None
        assert result["walk_minutes"] is None


# ---------------------------------------------------------------------------
# TestGetTravelTimesBatch
# ---------------------------------------------------------------------------
class TestGetTravelTimesBatch:
    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_batch_returns_results(self, mock_get, mock_sleep):
        """Batch call returns duration/distance for each destination."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": "Ok",
            "durations": [[0, 300.0, 600.0]],
            "distances": [[0, 5000.0, 10000.0]],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        destinations = [(35.80, -78.79), (35.81, -78.80)]
        results = get_travel_times_batch(35.79, -78.78, destinations, profile="car")

        assert len(results) == 2
        assert results[0]["duration_minutes"] == pytest.approx(5.0)
        assert results[0]["distance_miles"] == pytest.approx(3.1, abs=0.1)
        assert results[1]["duration_minutes"] == pytest.approx(10.0)

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_batch_error_returns_nones(self, mock_get, mock_sleep):
        """On HTTP error, returns list of None-valued dicts."""
        mock_get.side_effect = Exception("OSRM error")

        destinations = [(35.80, -78.79)]
        results = get_travel_times_batch(35.79, -78.78, destinations, profile="car")

        assert len(results) == 1
        assert results[0]["duration_minutes"] is None
        assert results[0]["distance_miles"] is None

    def test_batch_empty_destinations(self):
        """Empty destinations list returns empty list."""
        results = get_travel_times_batch(35.79, -78.78, [], profile="car")
        assert results == []

    @patch("pricepoint.data.housing.school_enrichment.time.sleep")
    @patch("pricepoint.data.housing.school_enrichment.httpx.get")
    def test_batch_non_ok_code(self, mock_get, mock_sleep):
        """Non-Ok OSRM response returns None-valued dicts."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": "InvalidOptions"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        destinations = [(35.80, -78.79)]
        results = get_travel_times_batch(35.79, -78.78, destinations, profile="car")

        assert len(results) == 1
        assert results[0]["duration_minutes"] is None
