"""Tests for the school enrichment module."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.housing.school_enrichment import (
    _normalize_school_name,
    enrich_property_schools,
    enrich_school,
    geocode_school_nominatim,
    get_osrm_route,
    get_travel_times,
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
# TestEnrichSchool
# ---------------------------------------------------------------------------
class TestEnrichSchool:
    def _make_school(self, name="Mills Park Elementary", address=None, location=None):
        school = MagicMock()
        school.id = 1
        school.name = name
        school.address = address
        school.nces_id = None
        school.needs_review = False
        school.location = location
        return school

    @patch("pricepoint.data.housing.school_enrichment.to_shape")
    @patch("pricepoint.data.housing.school_enrichment.get_travel_times")
    @patch("pricepoint.data.housing.school_enrichment.match_nces_school")
    def test_nces_match_enriches(self, mock_match, mock_travel, mock_to_shape):
        nces = MagicMock()
        nces.street = "100 Main St"
        nces.city = "Cary"
        nces.state = "NC"
        nces.zip_code = "27513"
        nces.nces_id = "001"
        nces.location = MagicMock()
        mock_match.return_value = nces
        mock_travel.return_value = {"drive_minutes": 5, "walk_minutes": 20}

        mock_point = MagicMock()
        mock_point.y = 35.80
        mock_point.x = -78.79
        mock_to_shape.return_value = mock_point

        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        school = self._make_school()

        result = enrich_school(session, school, 35.79, -78.78)
        assert result is True
        assert school.address == "100 Main St, Cary, NC, 27513"
        assert school.nces_id == "001"

    @patch("pricepoint.data.housing.school_enrichment.to_shape")
    @patch("pricepoint.data.housing.school_enrichment.geocode_school_nominatim")
    @patch("pricepoint.data.housing.school_enrichment.match_nces_school")
    def test_nominatim_fallback(self, mock_match, mock_nominatim, mock_to_shape):
        mock_match.return_value = None
        mock_nominatim.return_value = {
            "address": "Mills Park Elementary, Cary, NC",
            "lat": 35.79,
            "lon": -78.78,
        }

        mock_point = MagicMock()
        mock_point.y = 35.79
        mock_point.x = -78.78
        mock_to_shape.return_value = mock_point

        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        school = self._make_school()

        with patch("pricepoint.data.housing.school_enrichment.from_shape", return_value="geom"):
            result = enrich_school(session, school, 35.79, -78.78)

        assert result is True
        assert school.address == "Mills Park Elementary, Cary, NC"

    @patch("pricepoint.data.housing.school_enrichment.geocode_school_nominatim")
    @patch("pricepoint.data.housing.school_enrichment.match_nces_school")
    def test_both_fail_sets_needs_review(self, mock_match, mock_nominatim):
        mock_match.return_value = None
        mock_nominatim.return_value = None

        session = MagicMock()
        school = self._make_school()

        result = enrich_school(session, school, 35.79, -78.78)
        assert result is True
        assert school.needs_review is True

    @patch("pricepoint.data.housing.school_enrichment.get_travel_times")
    @patch("pricepoint.data.housing.school_enrichment.to_shape")
    @patch("pricepoint.data.housing.school_enrichment.match_nces_school")
    def test_updates_travel_times(self, mock_match, mock_to_shape, mock_travel):
        mock_match.return_value = None

        # School already has address and location
        school = self._make_school(address="100 Main St", location="geom")

        mock_point = MagicMock()
        mock_point.y = 35.80
        mock_point.x = -78.79
        mock_to_shape.return_value = mock_point

        mock_travel.return_value = {"drive_minutes": 5, "walk_minutes": 20}

        link = MagicMock()
        link.drive_minutes = None
        link.walk_minutes = None

        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = [link]

        result = enrich_school(session, school, 35.79, -78.78)
        assert result is True
        assert link.drive_minutes == 5
        assert link.walk_minutes == 20

    def test_skip_address_lookup_if_already_set(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        school = self._make_school(address="Already Set")

        result = enrich_school(session, school, 35.79, -78.78)
        # No location, so no travel times either
        assert result is False


# ---------------------------------------------------------------------------
# TestEnrichPropertySchools
# ---------------------------------------------------------------------------
class TestEnrichPropertySchools:
    @patch("pricepoint.data.housing.school_enrichment.enrich_school")
    def test_enriches_all_linked_schools(self, mock_enrich):
        mock_enrich.return_value = True

        link1 = MagicMock()
        link1.school_id = 1
        link2 = MagicMock()
        link2.school_id = 2

        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = [link1, link2]

        school1 = MagicMock()
        school2 = MagicMock()
        session.get.side_effect = [school1, school2]

        count = enrich_property_schools(session, 100, 35.79, -78.78)
        assert count == 2
        assert mock_enrich.call_count == 2

    @patch("pricepoint.data.housing.school_enrichment.enrich_school")
    def test_no_links(self, mock_enrich):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []

        count = enrich_property_schools(session, 100, 35.79, -78.78)
        assert count == 0
        mock_enrich.assert_not_called()

    @patch("pricepoint.data.housing.school_enrichment.enrich_school")
    def test_partial_enrichment(self, mock_enrich):
        mock_enrich.side_effect = [True, False]

        link1 = MagicMock()
        link1.school_id = 1
        link2 = MagicMock()
        link2.school_id = 2

        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = [link1, link2]

        school1 = MagicMock()
        school2 = MagicMock()
        session.get.side_effect = [school1, school2]

        count = enrich_property_schools(session, 100, 35.79, -78.78)
        assert count == 1
