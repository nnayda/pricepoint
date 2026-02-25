"""Tests for the school gold builder module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pricepoint.data.housing.school_gold_builder import (
    _build_grades_string,
    _extract_nces_extras,
    _find_district_id,
    _get_dirty_properties,
    _match_redfin_rating,
    _match_redfin_to_gold,
    build_schools_gold,
)


# ---------------------------------------------------------------------------
# _build_grades_string
# ---------------------------------------------------------------------------
class TestBuildGradesString:
    def test_pk_to_5(self):
        nces = MagicMock()
        nces.grades_low = "PK"
        nces.grades_high = "5"
        assert _build_grades_string(nces) == "PK-5"

    def test_same_grade(self):
        nces = MagicMock()
        nces.grades_low = "9"
        nces.grades_high = "9"
        assert _build_grades_string(nces) == "9"

    def test_none_both(self):
        nces = MagicMock()
        nces.grades_low = None
        nces.grades_high = None
        assert _build_grades_string(nces) is None

    def test_only_low(self):
        nces = MagicMock()
        nces.grades_low = "K"
        nces.grades_high = None
        assert _build_grades_string(nces) == "K"

    def test_only_high(self):
        nces = MagicMock()
        nces.grades_low = None
        nces.grades_high = "12"
        assert _build_grades_string(nces) == "12"


# ---------------------------------------------------------------------------
# _extract_nces_extras
# ---------------------------------------------------------------------------
class TestExtractNcesExtras:
    def test_full_extras(self):
        extras = {
            "MEMBER": "500",
            "FTE": "32.5",
            "STUTERATIO": "15.4",
            "FRELCH": "100",
            "REDLCH": "50",
            "TOTFRL": "150",
        }
        result = _extract_nces_extras(extras)
        assert result["enrollment"] == 500
        assert result["teachers"] == 32.5
        assert result["student_teacher_ratio"] == 15.4
        assert result["free_lunch_eligible"] == 100
        assert result["reduced_lunch_eligible"] == 50
        assert result["total_frl_eligible"] == 150

    def test_none_extras(self):
        assert _extract_nces_extras(None) == {}

    def test_empty_extras(self):
        # Empty dict is falsy, returns empty dict
        assert _extract_nces_extras({}) == {}

    def test_missing_keys(self):
        result = _extract_nces_extras({"SOME_OTHER": "value"})
        assert result["enrollment"] is None
        assert result["teachers"] is None

    def test_invalid_values(self):
        extras = {"MEMBER": "N/A", "FTE": "abc"}
        result = _extract_nces_extras(extras)
        assert result["enrollment"] is None
        assert result["teachers"] is None


# ---------------------------------------------------------------------------
# _find_district_id
# ---------------------------------------------------------------------------
class TestFindDistrictId:
    def test_returns_none_for_no_location(self):
        session = MagicMock()
        assert _find_district_id(session, None) is None

    def test_returns_district_id(self):
        session = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = 42
        result = _find_district_id(session, "mock_geom")
        assert result == 42

    def test_returns_none_when_not_found(self):
        session = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = None
        result = _find_district_id(session, "mock_geom")
        assert result is None


# ---------------------------------------------------------------------------
# _match_redfin_rating
# ---------------------------------------------------------------------------
class TestMatchRedfinRating:
    def test_returns_none_for_empty_list(self):
        session = MagicMock()
        assert _match_redfin_rating(session, "Test School", []) is None

    def test_returns_rating_on_good_match(self):
        session = MagicMock()
        candidate = MagicMock()
        candidate.name = "Mills Park Elementary School"
        candidate.rating = 9.0

        result = _match_redfin_rating(session, "Mills Park Elementary", [candidate])
        assert result == 9.0

    def test_returns_none_on_poor_match(self):
        session = MagicMock()
        candidate = MagicMock()
        candidate.name = "Completely Different Name"
        candidate.rating = 5.0

        result = _match_redfin_rating(session, "Mills Park Elementary", [candidate])
        assert result is None

    def test_picks_best_match(self):
        session = MagicMock()
        bad = MagicMock()
        bad.name = "Something Else"
        bad.rating = 3.0
        good = MagicMock()
        good.name = "Mills Park Elementary School"
        good.rating = 9.0

        result = _match_redfin_rating(session, "Mills Park Elementary", [bad, good])
        assert result == 9.0


# ---------------------------------------------------------------------------
# _match_redfin_to_gold
# ---------------------------------------------------------------------------
class TestMatchRedfinToGold:
    def test_good_match(self):
        redfin = MagicMock()
        redfin.name = "Mills Park Elementary"

        gold = MagicMock()
        gold.name = "Mills Park Elementary School"

        result = _match_redfin_to_gold(redfin, [gold])
        assert result is gold

    def test_no_match(self):
        redfin = MagicMock()
        redfin.name = "XYZ School"

        gold = MagicMock()
        gold.name = "Completely Different Name"

        result = _match_redfin_to_gold(redfin, [gold])
        assert result is None

    def test_empty_gold_list(self):
        redfin = MagicMock()
        redfin.name = "Test School"

        result = _match_redfin_to_gold(redfin, [])
        assert result is None


# ---------------------------------------------------------------------------
# build_schools_gold — UPSERT behavior
# ---------------------------------------------------------------------------
class TestBuildSchoolsGold:
    @patch("pricepoint.data.housing.school_gold_builder._match_redfin_rating")
    @patch("pricepoint.data.housing.school_gold_builder._find_district_id")
    def test_inserts_new_school(self, mock_district, mock_rating):
        """When no existing School row, a new one is added."""
        mock_district.return_value = 1
        mock_rating.return_value = 8.0

        nces = MagicMock()
        nces.nces_id = "370001000001"
        nces.name = "Test Elementary"
        nces.street = "100 Main St"
        nces.city = "Cary"
        nces.state = "NC"
        nces.zip_code = "27513"
        nces.school_type = "Regular"
        nces.school_level = "Elementary"
        nces.grades_low = "K"
        nces.grades_high = "5"
        nces.location = "mock_geom"
        nces.extras = {"MEMBER": "500", "FTE": "30", "STUTERATIO": "16.7"}

        session = MagicMock()
        session.scalar.return_value = 500  # minimum-count guard
        # First execute: NCES records, second: RedfinSchools, third: upsert lookup,
        # fourth: stale schools cleanup
        call_count = [0]

        def mock_execute(stmt):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # NCES records
                result.scalars.return_value.all.return_value = [nces]
            elif call_count[0] == 2:
                # Redfin schools
                result.scalars.return_value.all.return_value = []
            elif call_count[0] == 3:
                # Upsert lookup - no existing school
                result.scalar_one_or_none.return_value = None
            elif call_count[0] == 4:
                # Stale school check
                result.scalars.return_value.all.return_value = []
            return result

        session.execute.side_effect = mock_execute

        count = build_schools_gold(session)
        assert count == 1
        session.add.assert_called_once()

        added_school = session.add.call_args[0][0]
        assert added_school.nces_id == "370001000001"
        assert added_school.name == "Test Elementary"
        assert added_school.grades == "K-5"
        assert added_school.rating == 8.0
        assert added_school.district_id == 1
        assert added_school.enrollment == 500

    @patch("pricepoint.data.housing.school_gold_builder._match_redfin_rating")
    @patch("pricepoint.data.housing.school_gold_builder._find_district_id")
    def test_updates_existing_school(self, mock_district, mock_rating):
        """When an existing School row matches by nces_id, it is updated in place."""
        mock_district.return_value = 2
        mock_rating.return_value = 9.0

        nces = MagicMock()
        nces.nces_id = "370001000001"
        nces.name = "Test Elementary Updated"
        nces.street = "100 Main St"
        nces.city = "Cary"
        nces.state = "NC"
        nces.zip_code = "27513"
        nces.school_type = "Regular"
        nces.school_level = "Elementary"
        nces.grades_low = "K"
        nces.grades_high = "5"
        nces.location = "mock_geom"
        nces.extras = {"MEMBER": "600"}

        existing_school = MagicMock()
        existing_school.id = 42
        existing_school.nces_id = "370001000001"

        session = MagicMock()
        session.scalar.return_value = 500  # minimum-count guard
        call_count = [0]

        def mock_execute(stmt):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.scalars.return_value.all.return_value = [nces]
            elif call_count[0] == 2:
                result.scalars.return_value.all.return_value = []
            elif call_count[0] == 3:
                # Existing school found
                result.scalar_one_or_none.return_value = existing_school
            elif call_count[0] == 4:
                result.scalars.return_value.all.return_value = []
            return result

        session.execute.side_effect = mock_execute

        count = build_schools_gold(session)
        assert count == 1
        # Should NOT call session.add since we're updating an existing record
        session.add.assert_not_called()
        # Verify the existing school was updated
        assert existing_school.name == "Test Elementary Updated"
        assert existing_school.rating == 9.0
        assert existing_school.enrollment == 600
        assert existing_school.district_id == 2

    @patch("pricepoint.data.housing.school_gold_builder._match_redfin_rating")
    @patch("pricepoint.data.housing.school_gold_builder._find_district_id")
    def test_removes_stale_schools(self, mock_district, mock_rating):
        """Schools not in current NCES data are deleted with their PropertySchool links."""
        mock_district.return_value = None
        mock_rating.return_value = None

        nces = MagicMock()
        nces.nces_id = "001"
        nces.name = "Active School"
        nces.street = None
        nces.city = None
        nces.state = None
        nces.zip_code = None
        nces.school_type = None
        nces.school_level = None
        nces.grades_low = None
        nces.grades_high = None
        nces.location = None
        nces.extras = None

        stale_school = MagicMock()
        stale_school.id = 99
        stale_school.nces_id = "999"
        stale_school.name = "Closed School"

        session = MagicMock()
        session.scalar.return_value = 500  # minimum-count guard
        call_count = [0]

        def mock_execute(stmt):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.scalars.return_value.all.return_value = [nces]
            elif call_count[0] == 2:
                result.scalars.return_value.all.return_value = []
            elif call_count[0] == 3:
                # Upsert lookup
                result.scalar_one_or_none.return_value = None
            elif call_count[0] == 4:
                # Stale schools — one found
                result.scalars.return_value.all.return_value = [stale_school]
            return result

        session.execute.side_effect = mock_execute

        build_schools_gold(session)
        session.delete.assert_called_once_with(stale_school)

    @patch("pricepoint.data.housing.school_gold_builder._match_redfin_rating")
    @patch("pricepoint.data.housing.school_gold_builder._find_district_id")
    def test_pct_frl_calculation(self, mock_district, mock_rating):
        mock_district.return_value = None
        mock_rating.return_value = None

        nces = MagicMock()
        nces.nces_id = "001"
        nces.name = "Test"
        nces.street = None
        nces.city = None
        nces.state = None
        nces.zip_code = None
        nces.school_type = None
        nces.school_level = None
        nces.grades_low = None
        nces.grades_high = None
        nces.location = None
        nces.extras = {"MEMBER": "200", "TOTFRL": "100"}

        session = MagicMock()
        session.scalar.return_value = 500  # minimum-count guard
        call_count = [0]

        def mock_execute(stmt):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.scalars.return_value.all.return_value = [nces]
            elif call_count[0] == 2:
                result.scalars.return_value.all.return_value = []
            elif call_count[0] == 3:
                result.scalar_one_or_none.return_value = None
            elif call_count[0] == 4:
                result.scalars.return_value.all.return_value = []
            return result

        session.execute.side_effect = mock_execute

        build_schools_gold(session)
        added = session.add.call_args[0][0]
        assert added.pct_frl_eligible == 50.0


# ---------------------------------------------------------------------------
# _get_dirty_properties
# ---------------------------------------------------------------------------
class TestGetDirtyProperties:
    def test_returns_new_properties(self):
        """Properties with schools_built_at=None are dirty."""
        session = MagicMock()
        prop = MagicMock()
        prop.schools_built_at = None
        prop.location = "mock_geom"
        session.execute.return_value.scalars.return_value.all.return_value = [prop]

        result = _get_dirty_properties(session)
        assert len(result) == 1
        assert result[0] is prop

    def test_returns_retransformed_properties(self):
        """Properties where processed_at > schools_built_at are dirty."""
        session = MagicMock()
        prop = MagicMock()
        prop.schools_built_at = datetime(2024, 1, 1, tzinfo=UTC)
        prop.processed_at = datetime(2024, 6, 1, tzinfo=UTC)
        prop.location = "mock_geom"
        session.execute.return_value.scalars.return_value.all.return_value = [prop]

        result = _get_dirty_properties(session)
        assert len(result) == 1

    def test_skips_up_to_date_properties(self):
        """Properties where schools_built_at >= processed_at are skipped."""
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []

        result = _get_dirty_properties(session)
        assert len(result) == 0
