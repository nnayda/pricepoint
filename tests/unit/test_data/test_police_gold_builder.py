"""Tests for UCR mapping and police gold builder."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# UCR Mapping
# ---------------------------------------------------------------------------


class TestUcrMapping:
    """Tests for lookup_ucr function."""

    def test_string_code_lookup(self):
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("13A")
        assert group == "Assault"
        assert category == "Crimes Against Persons"
        assert offense_class == "Group A"

    def test_numeric_string_code_lookup(self):
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("200")
        assert group == "Arson"
        assert category == "Crimes Against Property"
        assert offense_class == "Group A"

    def test_int_like_code_lookup(self):
        """Codes that look like ints (e.g. '200') should be found."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("  200  ")
        assert group == "Arson"

    def test_none_code_returns_none(self):
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr(None)
        assert group is None
        assert category is None
        assert offense_class is None

    def test_empty_code_returns_none(self):
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("")
        assert group is None
        assert category is None
        assert offense_class is None

    def test_unknown_code_returns_none(self):
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("ZZZ")
        assert group is None
        assert category is None
        assert offense_class is None

    def test_lowercase_alpha_code(self):
        """Should handle lowercase input (normalized to upper)."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("13a")
        assert group == "Assault"

    def test_group_b_code(self):
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("90D")
        assert group == "All Other Offenses"
        assert category == "Group B"
        assert offense_class == "Group B"

    def test_new_nibrs_2025_code(self):
        """New standard NIBRS codes from 2025 spec should resolve."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("26H")
        assert group == "Fraud"
        assert category == "Crimes Against Property"
        assert offense_class == "Group A"

    def test_raleigh_srs_weapon_code(self):
        """Raleigh SRS-style local codes should resolve."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("51A")
        assert group == "Weapon Offenses"
        assert category == "Crimes Against Society"
        assert offense_class == "Group A"

    def test_raleigh_srs_assault_code(self):
        """Raleigh SRS-style assault code should resolve."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("25G")
        assert group == "Assault"
        assert category == "Crimes Against Persons"
        assert offense_class == "Group A"

    def test_raleigh_srs_group_b_code(self):
        """Raleigh SRS-style Group B code should resolve correctly."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("70C")
        assert group == "All Other Offenses"
        assert category == "Group B"
        assert offense_class == "Group B"

    def test_raleigh_animal_disturbance_code(self):
        """Raleigh 82x animal codes have Animal Disturbance offense class."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("82E")
        assert group == "Animal Disturbance"
        assert category == "Crimes Against Society"
        assert offense_class == "Animal Disturbance"

    def test_bribery_category_is_property(self):
        """510 Bribery should be Crimes Against Property per 2025 spec."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("510")
        assert group == "Bribery"
        assert category == "Crimes Against Property"

    def test_9910_not_in_map(self):
        """Cary 99xx codes should not be in the map."""
        from pricepoint.data.geospatial.ucr_mapping import lookup_ucr

        group, category, offense_class = lookup_ucr("9910")
        assert group is None
        assert category is None
        assert offense_class is None


class TestFuzzyMatchUcr:
    """Tests for fuzzy_match_ucr function."""

    def test_exact_match(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr("Aggravated Assault")
        assert code == "13A"
        assert group == "Assault"
        assert category == "Crimes Against Persons"
        assert offense_class == "Group A"

    def test_close_match(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr("Aggravated Assault - Weapon")
        # Should still fuzzy match to aggravated assault
        assert code is not None
        assert group is not None

    def test_no_match_gibberish(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr("xyzzy foo bar baz quux")
        assert code is None
        assert group is None
        assert category is None
        assert offense_class is None

    def test_none_input(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr(None)
        assert code is None
        assert group is None
        assert category is None
        assert offense_class is None

    def test_empty_string(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr("")
        assert code is None
        assert group is None
        assert category is None
        assert offense_class is None

    def test_robbery_match(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr("Robbery")
        assert code == "120"
        assert group == "Robbery"

    def test_shoplifting_match(self):
        from pricepoint.data.geospatial.ucr_mapping import fuzzy_match_ucr

        code, group, category, offense_class = fuzzy_match_ucr("Shoplifting")
        assert code == "23C"


class TestParseMorrisvilleDate:
    """Tests for _parse_morrisville_date."""

    def test_valid_date(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            _parse_morrisville_date,
        )

        result = _parse_morrisville_date("03/15/2024")
        assert result is not None
        assert result.month == 3
        assert result.day == 15
        assert result.year == 2024

    def test_none_returns_none(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            _parse_morrisville_date,
        )

        assert _parse_morrisville_date(None) is None

    def test_malformed_returns_none(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            _parse_morrisville_date,
        )

        assert _parse_morrisville_date("not-a-date") is None

    def test_empty_string_returns_none(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            _parse_morrisville_date,
        )

        assert _parse_morrisville_date("") is None

    def test_whitespace_stripped(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            _parse_morrisville_date,
        )

        result = _parse_morrisville_date("  01/01/2023  ")
        assert result is not None
        assert result.year == 2023


# ---------------------------------------------------------------------------
# Gold Builder
# ---------------------------------------------------------------------------


def _make_staging_row(model_name: str, **overrides):
    """Create a mock staging row for the given model."""
    row = MagicMock()

    if model_name == "raleigh":
        defaults = {
            "id": 1,
            "case_number": "R2024-001",
            "crime_code": "13A",
            "crime_description": "Aggravated Assault",
            "reported_block_address": "100 MAIN ST",
            "reported_date": datetime(2024, 6, 15),
            "latitude": 35.79,
            "longitude": -78.64,
            "location": MagicMock(),
        }
    elif model_name == "cary":
        defaults = {
            "id": 2,
            "incident_number": "C2024-001",
            "ucr": "23H",
            "crime_type": "Larceny",
            "geocode": "200 OAK DR",
            "date_from": datetime(2024, 6, 10),
            "lat": 35.78,
            "lon": -78.80,
            "location": MagicMock(),
        }
    elif model_name == "morrisville":
        defaults = {
            "id": 3,
            "inci_id": "M2024-001",
            "offense": "Simple Assault",
            "street": "300 ELM ST",
            "date_occu": "06/05/2024",
            "lat": 35.82,
            "lon": -78.83,
            "location": MagicMock(),
        }
    else:
        defaults = {}

    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


class TestBuildPoliceIncidentsGold:
    """Tests for build_police_incidents_gold."""

    def test_safety_guard_raises_on_low_count(self):
        """Should raise RuntimeError when total staging < 500."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        # Return low counts for all 3 tables
        session.scalar.side_effect = [10, 10, 10]

        with pytest.raises(RuntimeError, match="expected >= 500"):
            build_police_incidents_gold(session)

    def test_raleigh_field_mapping(self):
        """Raleigh rows produce RPD-prefixed incident_ids with UCR lookup."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [500, 50, 50]  # counts

        raleigh_row = _make_staging_row("raleigh")
        # Return rows per source
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = [raleigh_row]
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        # For upsert: no existing record
        upsert_result = MagicMock()
        upsert_result.scalar_one_or_none.return_value = None

        session.execute.side_effect = [
            raleigh_result,
            upsert_result,  # upsert check for raleigh row
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 1

        # Verify the added PoliceIncident
        added = session.add.call_args[0][0]
        assert added.incident_id == "RPD-R2024-001"
        assert added.crime_code == "13A"
        assert added.crime_group == "Assault"
        assert added.offense_class == "Group A"

    def test_cary_field_mapping(self):
        """Cary rows produce CPD-prefixed incident_ids."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [50, 500, 50]

        cary_row = _make_staging_row("cary")
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = []
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = [cary_row]
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        upsert_result = MagicMock()
        upsert_result.scalar_one_or_none.return_value = None

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            upsert_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 1
        added = session.add.call_args[0][0]
        assert added.incident_id == "CPD-C2024-001"
        assert added.crime_code == "23H"

    def test_morrisville_uses_fuzzy_match(self):
        """Morrisville rows use fuzzy matching for UCR codes."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [50, 50, 500]

        morrisville_row = _make_staging_row("morrisville")
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = []
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = [morrisville_row]

        upsert_result = MagicMock()
        upsert_result.scalar_one_or_none.return_value = None

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            morrisville_result,
            upsert_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 1
        added = session.add.call_args[0][0]
        assert added.incident_id == "MPD-M2024-001"
        # "Simple Assault" should fuzzy match to 13B
        assert added.crime_code == "13B"
        assert added.date_of_incident == date(2024, 6, 5)

    def test_upsert_updates_existing(self):
        """If incident_id already exists, should update not insert."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [500, 50, 50]

        raleigh_row = _make_staging_row("raleigh")
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = [raleigh_row]
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        existing_record = MagicMock()
        upsert_result = MagicMock()
        upsert_result.scalar_one_or_none.return_value = existing_record

        session.execute.side_effect = [
            raleigh_result,
            upsert_result,
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 1
        # Should NOT have called session.add (update, not insert)
        session.add.assert_not_called()
        # Should have updated existing record's attributes
        assert existing_record.crime_code == "13A"

    def test_duplicate_case_number_no_unique_violation(self):
        """Multiple staging rows with the same case_number should not fail.

        Raleigh data can have multiple offenses per incident (same case_number,
        different crime codes). The gold builder should handle this by updating
        the pending in-memory object rather than inserting duplicates.
        """
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [500, 50, 50]

        # Two staging rows with the same case_number but different offenses
        row1 = _make_staging_row(
            "raleigh",
            case_number="P26006816",
            crime_code="54Z",
            crime_description="Drug Equipment/Paraphernalia",
        )
        row2 = _make_staging_row(
            "raleigh",
            case_number="P26006816",
            crime_code="54C",
            crime_description="Drug Violation/Felony",
        )

        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = [row1, row2]
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        # Only the first occurrence triggers a DB lookup (returns None = new)
        upsert_result = MagicMock()
        upsert_result.scalar_one_or_none.return_value = None

        session.execute.side_effect = [
            raleigh_result,
            upsert_result,  # DB lookup for first row1
            # row2 is handled via pending dict — no DB query
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 2  # both rows counted

        # Only one session.add call (first occurrence creates, second updates in-memory)
        assert session.add.call_count == 1
        added = session.add.call_args[0][0]
        assert added.incident_id == "RPD-P26006816"
        # Last write wins — row2's crime_code should be on the object
        assert added.crime_code == "54C"
        assert added.crime_description == "Drug Violation/Felony"
        # Both codes are now valid mapped codes
        assert added.crime_group == "Drug Offenses"
        assert added.crime_category == "Crimes Against Society"
        assert added.offense_class == "Group A"

    def test_cary_99xx_code_skipped(self):
        """Cary 99xx non-criminal codes should be skipped."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [50, 500, 50]

        cary_row = _make_staging_row("cary", ucr="9910", crime_type="Found Property")
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = []
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = [cary_row]
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 0
        session.add.assert_not_called()

    def test_raleigh_81x_code_skipped(self):
        """Raleigh 81x non-criminal codes should be skipped."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [500, 50, 50]

        raleigh_row = _make_staging_row(
            "raleigh", crime_code="81A", crime_description="Deceased Person"
        )
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = [raleigh_row]
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 0
        session.add.assert_not_called()

    def test_null_crime_code_skipped(self):
        """Records with null crime_code should be skipped."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [50, 500, 50]

        cary_row = _make_staging_row("cary", ucr=None, crime_type="Unknown")
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = []
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = [cary_row]
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 0
        session.add.assert_not_called()

    def test_empty_crime_code_skipped(self):
        """Records with empty string crime_code should be skipped."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [500, 50, 50]

        raleigh_row = _make_staging_row("raleigh", crime_code="", crime_description="Unknown")
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = [raleigh_row]
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 0
        session.add.assert_not_called()

    def test_zero_coordinate_skipped(self):
        """Records with lat=0 or lon=0 should be skipped."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.side_effect = [500, 50, 50]

        raleigh_row = _make_staging_row("raleigh", latitude=0, longitude=0)
        raleigh_result = MagicMock()
        raleigh_result.scalars.return_value.all.return_value = [raleigh_row]
        cary_result = MagicMock()
        cary_result.scalars.return_value.all.return_value = []
        morrisville_result = MagicMock()
        morrisville_result.scalars.return_value.all.return_value = []

        session.execute.side_effect = [
            raleigh_result,
            cary_result,
            morrisville_result,
        ]

        count = build_police_incidents_gold(session)
        assert count == 0
        session.add.assert_not_called()


class TestVerifyPoliceIncidentsGold:
    """Tests for verify_police_incidents_gold."""

    def test_empty_table_raises(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            verify_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.return_value = 0

        with pytest.raises(RuntimeError, match="No records"):
            verify_police_incidents_gold(session)

    def test_populated_returns_count(self):
        from pricepoint.data.geospatial.police_gold_builder import (
            verify_police_incidents_gold,
        )

        session = MagicMock()
        session.scalar.return_value = 1500

        result = verify_police_incidents_gold(session)
        assert result == {"police_incidents": 1500}
