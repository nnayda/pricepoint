"""Tests for Census ACS demographic data collector."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from pricepoint.data.geospatial.census_demographics import (
    _COUNT_FIELDS,
    _MEDIAN_FIELDS,
    _US_STATE_FIPS,
    _aggregate_age_brackets,
    _aggregate_education,
    _extract_geoid,
    _fetch_acs_data,
    _fetch_nationwide,
    _level_exists,
    _map_demographic_kwargs,
    _map_record,
    _safe_float,
    _safe_int,
    compute_subdivision_demographics,
    fetch_acs_block_group_demographics,
    fetch_acs_county_sub_demographics,
    fetch_acs_summary_demographics,
    fetch_acs_tract_demographics,
    verify_acs_demographics,
)

_PATCH_LEVEL_EXISTS = "pricepoint.data.geospatial.census_demographics._level_exists"
_PATCH_STATE_FIPS = "pricepoint.data.geospatial.census_demographics._US_STATE_FIPS"

# -- Helpers ------------------------------------------------------------------


def _make_settings(**overrides):
    """Create a mock settings object."""
    s = MagicMock()
    s.census_api_key = "test-key"
    s.census_acs_base_url = "https://api.census.gov/data"
    s.census_acs_vintages = [2019]
    s.census_acs_block_group_min_year = 2014
    s.tiger_state_fips = "37"
    s.tiger_county_fips = "183"
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _mock_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.add_all = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


def _make_row(**overrides):
    """Build a minimal Census API row dict for testing."""
    row = {
        "state": "37",
        "county": "183",
        "tract": "052801",
        "NAME": "Census Tract 528.01",
        "B01001_001E": "5000",
        "B01001_002E": "2400",
        "B01001_026E": "2600",
        "B01002_001E": "35.2",
        "B02001_002E": "3000",
        "B02001_003E": "1000",
        "B02001_004E": "50",
        "B02001_005E": "400",
        "B02001_006E": "10",
        "B02001_007E": "200",
        "B02001_008E": "340",
        "B03003_001E": "5000",
        "B03003_002E": "4500",
        "B03003_003E": "500",
        "B19001_001E": "2000",
        "B19001_002E": "100",
        "B19001_003E": "50",
        "B19001_004E": "60",
        "B19001_005E": "70",
        "B19001_006E": "80",
        "B19001_007E": "90",
        "B19001_008E": "100",
        "B19001_009E": "110",
        "B19001_010E": "120",
        "B19001_011E": "130",
        "B19001_012E": "140",
        "B19001_013E": "150",
        "B19001_014E": "160",
        "B19001_015E": "170",
        "B19001_016E": "180",
        "B19001_017E": "190",
        "B19013_001E": "65000",
        "B15003_001E": "3500",
        "B25003_001E": "1800",
        "B25003_002E": "1200",
        "B25003_003E": "600",
        "B25077_001E": "285000",
    }
    row.update(overrides)
    return row


# -- _safe_int tests ----------------------------------------------------------


class TestSafeInt:
    def test_valid_integer(self):
        assert _safe_int("42") == 42

    def test_none_returns_none(self):
        assert _safe_int(None) is None

    def test_empty_string_returns_none(self):
        assert _safe_int("") is None

    def test_sentinel_returns_none(self):
        assert _safe_int("-666666666") is None

    def test_invalid_string_returns_none(self):
        assert _safe_int("abc") is None

    def test_negative_value(self):
        assert _safe_int("-100") == -100

    def test_zero(self):
        assert _safe_int("0") == 0


# -- _safe_float tests --------------------------------------------------------


class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float("35.2") == 35.2

    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_sentinel_returns_none(self):
        assert _safe_float("-666666666") is None

    def test_integer_string(self):
        assert _safe_float("42") == 42.0

    def test_empty_string_returns_none(self):
        assert _safe_float("") is None


# -- _extract_geoid tests -----------------------------------------------------


class TestExtractGeoid:
    def test_tract_geoid(self):
        row = {"state": "37", "county": "183", "tract": "052801"}
        assert _extract_geoid(row, "tract") == "37183052801"

    def test_block_group_geoid(self):
        row = {"state": "37", "county": "183", "tract": "052801", "block group": "1"}
        assert _extract_geoid(row, "block group") == "371830528011"

    def test_tract_geoid_length(self):
        geoid = _extract_geoid({"state": "37", "county": "183", "tract": "052801"}, "tract")
        assert len(geoid) == 11

    def test_block_group_geoid_length(self):
        geoid = _extract_geoid(
            {"state": "37", "county": "183", "tract": "052801", "block group": "2"},
            "block group",
        )
        assert len(geoid) == 12

    def test_us_geoid(self):
        row = {"us": "1"}
        assert _extract_geoid(row, "us") == "1"

    def test_us_geoid_default(self):
        assert _extract_geoid({}, "us") == "1"

    def test_state_geoid(self):
        row = {"state": "37"}
        assert _extract_geoid(row, "state") == "37"

    def test_county_geoid(self):
        row = {"state": "37", "county": "183"}
        assert _extract_geoid(row, "county") == "37183"

    def test_county_subdivision_geoid(self):
        row = {"state": "37", "county": "183", "county subdivision": "90280"}
        assert _extract_geoid(row, "county subdivision") == "3718390280"


# -- _aggregate_age_brackets tests --------------------------------------------


class TestAggregateAgeBrackets:
    def test_basic_aggregation(self):
        row = {}
        # Set male under-18 vars (003-006) to 100 each
        for i in range(3, 7):
            row[f"B01001_{i:03d}E"] = "100"
        # Set female under-18 vars (027-030) to 100 each
        for i in range(27, 31):
            row[f"B01001_{i:03d}E"] = "100"
        result = _aggregate_age_brackets(row)
        assert result["pop_under_18"] == 800

    def test_missing_vars_returns_none(self):
        result = _aggregate_age_brackets({})
        assert result["pop_under_18"] is None
        assert result["pop_65_plus"] is None

    def test_partial_data(self):
        row = {"B01001_003E": "50"}
        result = _aggregate_age_brackets(row)
        assert result["pop_under_18"] == 50

    def test_all_brackets_populated(self):
        row = {}
        # under 18: male 003-006, female 027-030 (8 vars)
        for i in list(range(3, 7)) + list(range(27, 31)):
            row[f"B01001_{i:03d}E"] = "10"
        # 18-22: male 007-009, female 031-033 (6 vars)
        for i in list(range(7, 10)) + list(range(31, 34)):
            row[f"B01001_{i:03d}E"] = "20"
        # 23-29: male 010-011, female 034-035 (4 vars)
        for i in list(range(10, 12)) + list(range(34, 36)):
            row[f"B01001_{i:03d}E"] = "30"
        # 30-39: male 012-013, female 036-037 (4 vars)
        for i in list(range(12, 14)) + list(range(36, 38)):
            row[f"B01001_{i:03d}E"] = "40"
        # 40-49: male 014-015, female 038-039 (4 vars)
        for i in list(range(14, 16)) + list(range(38, 40)):
            row[f"B01001_{i:03d}E"] = "50"
        # 50-64: male 016-019, female 040-043 (8 vars)
        for i in list(range(16, 20)) + list(range(40, 44)):
            row[f"B01001_{i:03d}E"] = "60"
        # 65+: male 020-025, female 044-049 (12 vars)
        for i in list(range(20, 26)) + list(range(44, 50)):
            row[f"B01001_{i:03d}E"] = "70"
        result = _aggregate_age_brackets(row)
        assert result["pop_under_18"] == 80  # 8 * 10
        assert result["pop_18_to_22"] == 120  # 6 * 20
        assert result["pop_23_to_29"] == 120  # 4 * 30
        assert result["pop_30_to_39"] == 160  # 4 * 40
        assert result["pop_40_to_49"] == 200  # 4 * 50
        assert result["pop_50_to_64"] == 480  # 8 * 60
        assert result["pop_65_plus"] == 840  # 12 * 70


# -- _aggregate_education tests -----------------------------------------------


class TestAggregateEducation:
    def test_basic_aggregation(self):
        row = {"B15003_001E": "1000"}
        # less than HS: 002-016 (15 vars)
        for i in range(2, 17):
            row[f"B15003_{i:03d}E"] = "10"
        # HS diploma + GED: 017-018
        row["B15003_017E"] = "200"
        row["B15003_018E"] = "50"
        # Some college: 019-021
        for i in range(19, 22):
            row[f"B15003_{i:03d}E"] = "100"
        # Bachelor's: 022
        row["B15003_022E"] = "150"
        # Graduate+: 023-025
        for i in range(23, 26):
            row[f"B15003_{i:03d}E"] = "50"

        result = _aggregate_education(row, 2019)
        assert result["edu_total"] == 1000
        assert result["edu_less_than_hs"] == 150  # 15 * 10
        assert result["edu_high_school"] == 250  # 200 + 50
        assert result["edu_some_college"] == 300  # 3 * 100
        assert result["edu_bachelors"] == 150
        assert result["edu_graduate_plus"] == 150  # 3 * 50

    def test_missing_vars(self):
        result = _aggregate_education({}, 2019)
        assert result["edu_total"] is None
        assert result["edu_less_than_hs"] is None

    def test_b15002_fallback_for_old_vintage(self):
        """Pre-2014 vintages use B15002 (Sex by Educational Attainment)."""
        row = {"B15002_001E": "500"}
        # Male less than HS (003-010): 8 vars
        for i in range(3, 11):
            row[f"B15002_{i:03d}E"] = "5"
        # Female less than HS (020-027): 8 vars
        for i in range(20, 28):
            row[f"B15002_{i:03d}E"] = "5"
        # Male HS (011) + Female HS (028)
        row["B15002_011E"] = "50"
        row["B15002_028E"] = "60"
        # Male some college (012-014) + Female (029-031)
        for i in range(12, 15):
            row[f"B15002_{i:03d}E"] = "20"
        for i in range(29, 32):
            row[f"B15002_{i:03d}E"] = "20"
        # Male bachelor's (015) + Female (032)
        row["B15002_015E"] = "40"
        row["B15002_032E"] = "35"
        # Male graduate+ (016-018) + Female (033-035)
        for i in range(16, 19):
            row[f"B15002_{i:03d}E"] = "10"
        for i in range(33, 36):
            row[f"B15002_{i:03d}E"] = "10"

        result = _aggregate_education(row, 2009)
        assert result["edu_total"] == 500
        assert result["edu_less_than_hs"] == 80  # 16 * 5
        assert result["edu_high_school"] == 110  # 50 + 60
        assert result["edu_some_college"] == 120  # 6 * 20
        assert result["edu_bachelors"] == 75  # 40 + 35
        assert result["edu_graduate_plus"] == 60  # 6 * 10

    def test_b15002_missing_vars(self):
        result = _aggregate_education({}, 2009)
        assert result["edu_total"] is None
        assert result["edu_less_than_hs"] is None


# -- _map_demographic_kwargs tests -------------------------------------------


class TestMapDemographicKwargs:
    def test_extracts_all_fields(self):
        row = _make_row()
        kwargs = _map_demographic_kwargs(row, 2019)
        assert kwargs["acs_year"] == 2019
        assert kwargs["total_population"] == 5000
        assert kwargs["median_age"] == 35.2
        assert kwargs["median_household_income"] == 65000
        assert kwargs["housing_owner_occupied"] == 1200

    def test_sentinel_values_become_none(self):
        row = _make_row(**{"B19013_001E": "-666666666"})
        kwargs = _map_demographic_kwargs(row, 2019)
        assert kwargs["median_household_income"] is None


# -- _map_record tests -------------------------------------------------------


class TestMapRecord:
    def test_maps_tract(self):
        row = _make_row()
        record = _map_record(row, 2019, "tract", "tract")
        assert record.geography_level == "tract"
        assert record.geoid == "37183052801"
        assert record.acs_year == 2019
        assert record.total_population == 5000

    def test_maps_block_group(self):
        row = _make_row(**{"block group": "2"})
        record = _map_record(row, 2019, "block group", "block_group")
        assert record.geography_level == "block_group"
        assert record.geoid == "371830528012"

    def test_maps_us(self):
        row = _make_row(**{"us": "1"})
        record = _map_record(row, 2019, "us", "us")
        assert record.geography_level == "us"
        assert record.geoid == "1"

    def test_maps_state(self):
        row = _make_row()
        record = _map_record(row, 2019, "state", "state")
        assert record.geography_level == "state"
        assert record.geoid == "37"

    def test_maps_county(self):
        row = _make_row()
        record = _map_record(row, 2019, "county", "county")
        assert record.geography_level == "county"
        assert record.geoid == "37183"

    def test_maps_county_subdivision(self):
        row = _make_row(**{"county subdivision": "90280"})
        record = _map_record(row, 2019, "county subdivision", "county_subdivision")
        assert record.geography_level == "county_subdivision"
        assert record.geoid == "3718390280"

    def test_sentinel_values_become_none(self):
        row = _make_row(**{"B19013_001E": "-666666666", "B25077_001E": "-666666666"})
        record = _map_record(row, 2019, "tract", "tract")
        assert record.median_household_income is None
        assert record.median_home_value is None

    def test_name_field(self):
        row = _make_row()
        record = _map_record(row, 2019, "tract", "tract")
        assert record.name == "Census Tract 528.01"


# -- _fetch_acs_data tests ----------------------------------------------------


class TestFetchAcsData:
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_single_chunk(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "state", "county", "tract"],
            ["Tract 1", "5000", "37", "183", "052801"],
        ]
        mock_get.return_value = mock_response

        result = _fetch_acs_data(2019, ["B01001_001E"], "tract", "37", "183")
        assert len(result) == 1
        assert result[0]["B01001_001E"] == "5000"

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_multi_chunk_merge(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()

        # Two chunks, same GEOID should merge
        resp1 = MagicMock()
        resp1.json.return_value = [
            ["NAME", "VAR_A", "state", "county", "tract"],
            ["Tract 1", "100", "37", "183", "052801"],
        ]
        resp2 = MagicMock()
        resp2.json.return_value = [
            ["NAME", "VAR_B", "state", "county", "tract"],
            ["Tract 1", "200", "37", "183", "052801"],
        ]
        mock_get.side_effect = [resp1, resp2]

        # 50 vars in first chunk, 1 in second → forces 2 requests
        vars_list = [f"VAR_{i}" for i in range(50)] + ["VAR_B"]
        # Override VAR_A to be in the first chunk
        vars_list[0] = "VAR_A"
        result = _fetch_acs_data(2019, vars_list, "tract", "37", "183")

        assert len(result) == 1
        assert result[0]["VAR_A"] == "100"
        assert result[0]["VAR_B"] == "200"

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_http_error_raises(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_get.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=MagicMock(), response=MagicMock(status_code=500)
        )

        with pytest.raises(httpx.HTTPStatusError):
            _fetch_acs_data(2019, ["B01001_001E"], "tract", "37", "183")

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_missing_api_key_raises(self, mock_settings):
        mock_settings.return_value = _make_settings(census_api_key="")

        with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
            _fetch_acs_data(2019, ["B01001_001E"], "tract", "37", "183")

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_block_group_geo_params(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "state", "county", "tract", "block group"],
            ["BG 1", "500", "37", "183", "052801", "1"],
        ]
        mock_get.return_value = mock_response

        result = _fetch_acs_data(2019, ["B01001_001E"], "block group", "37", "183")
        assert len(result) == 1
        assert result[0]["block group"] == "1"

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_us_level_no_in_param(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "us"],
            ["United States", "330000000", "1"],
        ]
        mock_get.return_value = mock_response

        result = _fetch_acs_data(2019, ["B01001_001E"], "us")
        assert len(result) == 1
        assert result[0]["B01001_001E"] == "330000000"
        # Verify no 'in' param was sent
        _, kwargs = mock_get.call_args
        assert "in" not in kwargs.get("params", {})

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_state_level(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "state"],
            ["North Carolina", "10000000", "37"],
        ]
        mock_get.return_value = mock_response

        result = _fetch_acs_data(2019, ["B01001_001E"], "state", "37")
        assert len(result) == 1
        assert result[0]["state"] == "37"

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_county_level(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "state", "county"],
            ["Wake County", "1100000", "37", "183"],
        ]
        mock_get.return_value = mock_response

        result = _fetch_acs_data(2019, ["B01001_001E"], "county", "37", "183")
        assert len(result) == 1
        assert result[0]["B01001_001E"] == "1100000"

    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    @patch("pricepoint.data.geospatial.census_demographics.httpx.get")
    def test_county_subdivision_level(self, mock_get, mock_settings):
        mock_settings.return_value = _make_settings()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            ["NAME", "B01001_001E", "state", "county", "county subdivision"],
            ["Cary township", "170000", "37", "183", "90280"],
        ]
        mock_get.return_value = mock_response

        result = _fetch_acs_data(2019, ["B01001_001E"], "county subdivision", "37", "183")
        assert len(result) == 1
        assert result[0]["county subdivision"] == "90280"


# -- _level_exists tests ------------------------------------------------------


class TestLevelExists:
    def test_returns_true_when_count_positive(self):
        session = _mock_session()
        session.execute.return_value.scalar.return_value = 5
        assert _level_exists(session, 2019, "tract") is True

    def test_returns_false_when_count_zero(self):
        session = _mock_session()
        session.execute.return_value.scalar.return_value = 0
        assert _level_exists(session, 2019, "tract") is False

    def test_returns_false_when_count_none(self):
        session = _mock_session()
        session.execute.return_value.scalar.return_value = None
        assert _level_exists(session, 2019, "tract") is False


# -- _US_STATE_FIPS tests ----------------------------------------------------


class TestUsStateFips:
    def test_contains_51_entries(self):
        """50 states + DC = 51 FIPS codes."""
        assert len(_US_STATE_FIPS) == 51

    def test_includes_dc(self):
        assert "11" in _US_STATE_FIPS

    def test_includes_nc(self):
        assert "37" in _US_STATE_FIPS

    def test_all_two_digit_strings(self):
        assert all(len(f) == 2 and f.isdigit() for f in _US_STATE_FIPS)


# -- _fetch_nationwide tests -------------------------------------------------


class TestFetchNationwide:
    @patch(_PATCH_STATE_FIPS, ["37", "06"])
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_iterates_states(self, mock_settings, mock_fetch):
        mock_settings.return_value = _make_settings()
        mock_fetch.return_value = [_make_row()]

        records = _fetch_nationwide(2019, "tract", "tract")

        assert mock_fetch.call_count == 2
        # 2 states × 1 row each = 2 records
        assert len(records) == 2
        assert all(r.geography_level == "tract" for r in records)

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_passes_state_fips(self, mock_settings, mock_fetch):
        mock_settings.return_value = _make_settings()
        mock_fetch.return_value = [_make_row()]

        _fetch_nationwide(2019, "tract", "tract")

        mock_fetch.assert_called_once()
        assert mock_fetch.call_args.kwargs["state_fips"] == "37"

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_empty_state_returns_no_records(self, mock_settings, mock_fetch):
        mock_settings.return_value = _make_settings()
        mock_fetch.return_value = []

        records = _fetch_nationwide(2019, "tract", "tract")

        assert len(records) == 0


# -- fetch_acs_tract_demographics tests ---------------------------------------


class TestFetchAcsTractDemographics:
    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_iterates_all_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        settings = _make_settings(census_acs_vintages=[2009, 2014, 2019])
        mock_settings.return_value = settings
        mock_fetch.return_value = [_make_row()]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_tract_demographics()

        # 1 state × 3 vintages = 3 fetch calls
        assert mock_fetch.call_count == 3
        # Verify called with each year
        years_called = [c.args[0] for c in mock_fetch.call_args_list]
        assert years_called == [2009, 2014, 2019]

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_rollback_on_error(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        mock_fetch.side_effect = RuntimeError("API error")
        session = _mock_session()
        mock_session_cls.return_value = session

        with pytest.raises(RuntimeError):
            fetch_acs_tract_demographics()

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_records_have_tract_geography_level(
        self, mock_settings, mock_fetch, mock_session_cls, _le
    ):
        mock_settings.return_value = _make_settings()
        mock_fetch.return_value = [_make_row()]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_tract_demographics()

        records = session.add_all.call_args[0][0]
        assert all(r.geography_level == "tract" for r in records)

    @patch(_PATCH_LEVEL_EXISTS, return_value=True)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_skips_existing_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_tract_demographics()

        mock_fetch.assert_not_called()
        session.add_all.assert_not_called()

    @patch(_PATCH_STATE_FIPS, ["37", "06"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_iterates_all_states(self, mock_settings, mock_fetch, mock_session_cls, _le):
        """Verify per-state iteration with multiple states."""
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        mock_fetch.return_value = [_make_row()]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_tract_demographics()

        # 2 states × 1 vintage = 2 fetch calls
        assert mock_fetch.call_count == 2
        states_called = [c.kwargs.get("state_fips") for c in mock_fetch.call_args_list]
        assert states_called == ["37", "06"]


# -- fetch_acs_block_group_demographics tests ---------------------------------


class TestFetchAcsBlockGroupDemographics:
    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_iterates_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        settings = _make_settings(census_acs_vintages=[2019, 2024])
        mock_settings.return_value = settings
        mock_fetch.return_value = [_make_row(**{"block group": "1"})]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_block_group_demographics()

        # 1 state × 2 vintages = 2 fetch calls
        assert mock_fetch.call_count == 2

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_records_have_block_group_geography_level(
        self, mock_settings, mock_fetch, mock_session_cls, _le
    ):
        mock_settings.return_value = _make_settings()
        mock_fetch.return_value = [_make_row(**{"block group": "1"})]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_block_group_demographics()

        records = session.add_all.call_args[0][0]
        assert all(r.geography_level == "block_group" for r in records)

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_skips_vintages_below_min_year(self, mock_settings, mock_fetch, mock_session_cls, _le):
        settings = _make_settings(
            census_acs_vintages=[2009, 2014, 2019],
            census_acs_block_group_min_year=2014,
        )
        mock_settings.return_value = settings
        mock_fetch.return_value = [_make_row(**{"block group": "1"})]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_block_group_demographics()

        # Only 2014 and 2019 should be fetched (2009 skipped), 1 state each
        assert mock_fetch.call_count == 2
        years_called = [c.args[0] for c in mock_fetch.call_args_list]
        assert years_called == [2014, 2019]

    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_no_eligible_vintages_returns_early(self, mock_settings, mock_fetch, mock_session_cls):
        settings = _make_settings(
            census_acs_vintages=[2009],
            census_acs_block_group_min_year=2014,
        )
        mock_settings.return_value = settings

        fetch_acs_block_group_demographics()

        mock_fetch.assert_not_called()
        mock_session_cls.assert_not_called()

    @patch(_PATCH_LEVEL_EXISTS, return_value=True)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_skips_existing_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_block_group_demographics()

        mock_fetch.assert_not_called()
        session.add_all.assert_not_called()


# -- fetch_acs_summary_demographics tests ------------------------------------


class TestFetchAcsSummaryDemographics:
    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_fetches_three_levels_per_vintage(
        self, mock_settings, mock_fetch, mock_session_cls, _le
    ):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        mock_fetch.return_value = [_make_row(**{"us": "1"})]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_summary_demographics()

        # us (1) + state (1) + county (1 state) = 3 fetch calls
        assert mock_fetch.call_count == 3

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_multiple_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2014, 2019])
        mock_fetch.return_value = [_make_row(**{"us": "1"})]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_summary_demographics()

        # (us + state + county) × 2 vintages = 6 calls
        assert mock_fetch.call_count == 6

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_rollback_on_error(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        mock_fetch.side_effect = RuntimeError("API error")
        session = _mock_session()
        mock_session_cls.return_value = session

        with pytest.raises(RuntimeError):
            fetch_acs_summary_demographics()

        session.rollback.assert_called_once()
        session.close.assert_called_once()

    @patch(_PATCH_LEVEL_EXISTS, return_value=True)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_skips_existing_levels(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_summary_demographics()

        mock_fetch.assert_not_called()
        session.add_all.assert_not_called()


# -- fetch_acs_county_sub_demographics tests ---------------------------------


class TestFetchAcsCountySubDemographics:
    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_iterates_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        mock_fetch.return_value = [
            _make_row(**{"county subdivision": "90280"}),
            _make_row(**{"county subdivision": "12345"}),
        ]
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_county_sub_demographics()

        # 1 state × 1 vintage = 1 fetch call
        assert mock_fetch.call_count == 1
        records = session.add_all.call_args[0][0]
        assert len(records) == 2
        assert all(r.geography_level == "county_subdivision" for r in records)

    @patch(_PATCH_STATE_FIPS, ["37"])
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_rollback_on_error(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        mock_fetch.side_effect = RuntimeError("API error")
        session = _mock_session()
        mock_session_cls.return_value = session

        with pytest.raises(RuntimeError):
            fetch_acs_county_sub_demographics()

        session.rollback.assert_called_once()

    @patch(_PATCH_LEVEL_EXISTS, return_value=True)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics._fetch_acs_data")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_skips_existing_vintages(self, mock_settings, mock_fetch, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        session = _mock_session()
        mock_session_cls.return_value = session

        fetch_acs_county_sub_demographics()

        mock_fetch.assert_not_called()
        session.add_all.assert_not_called()


# -- compute_subdivision_demographics tests ----------------------------------


class TestComputeSubdivisionDemographics:
    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_basic_computation(self, mock_settings, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        mock_session_cls.return_value = session

        # Mock SQL result with column names matching the query output
        columns = ["subdivision_id", "subdivision_name"] + _COUNT_FIELDS + _MEDIAN_FIELDS
        row_values = [329933, "Test Subdivision"]
        # Set count fields to various values
        for i, _ in enumerate(_COUNT_FIELDS):
            row_values.append(1000 + i)
        # Set median fields
        row_values.append(35.5)  # median_age
        row_values.append(65000)  # median_household_income
        row_values.append(285000)  # median_home_value

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [tuple(row_values)]
        mock_result.keys.return_value = columns
        session.execute.return_value = mock_result

        compute_subdivision_demographics()

        # Verify records were created
        assert session.add_all.call_count == 1
        records = session.add_all.call_args[0][0]
        assert len(records) == 1
        assert records[0].geography_level == "subdivision"
        assert records[0].geoid == "subdiv_329933"
        assert records[0].name == "Test Subdivision"
        assert records[0].total_population == 1000
        assert records[0].median_age == 35.5

    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_no_overlaps(self, mock_settings, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        mock_session_cls.return_value = session

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.keys.return_value = []
        session.execute.return_value = mock_result

        compute_subdivision_demographics()

        # No records to insert, so add_all should not be called (empty batch)
        session.add_all.assert_not_called()

    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_rollback_on_error(self, mock_settings, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        mock_session_cls.return_value = session
        session.execute.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            compute_subdivision_demographics()

        session.rollback.assert_called_once()

    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_multiple_subdivisions(self, mock_settings, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        mock_session_cls.return_value = session

        columns = ["subdivision_id", "subdivision_name"] + _COUNT_FIELDS + _MEDIAN_FIELDS
        rows = []
        for obj_id, name in [(100, "Sub A"), (200, "Sub B")]:
            vals = [obj_id, name]
            for _ in _COUNT_FIELDS:
                vals.append(500)
            vals.extend([30.0, 50000, 200000])  # medians
            rows.append(tuple(vals))

        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_result.keys.return_value = columns
        session.execute.return_value = mock_result

        compute_subdivision_demographics()

        records = session.add_all.call_args[0][0]
        assert len(records) == 2
        geoids = {r.geoid for r in records}
        assert geoids == {"subdiv_100", "subdiv_200"}

    @patch(_PATCH_LEVEL_EXISTS, return_value=False)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_null_median_values(self, mock_settings, mock_session_cls, _le):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        mock_session_cls.return_value = session

        columns = ["subdivision_id", "subdivision_name"] + _COUNT_FIELDS + _MEDIAN_FIELDS
        vals = [999, "Sparse Sub"]
        for _ in _COUNT_FIELDS:
            vals.append(0)
        vals.extend([None, None, None])  # null medians

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [tuple(vals)]
        mock_result.keys.return_value = columns
        session.execute.return_value = mock_result

        compute_subdivision_demographics()

        records = session.add_all.call_args[0][0]
        assert records[0].median_age is None
        assert records[0].median_household_income is None
        assert records[0].median_home_value is None

    @patch(_PATCH_LEVEL_EXISTS, return_value=True)
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_skips_existing_vintages(self, mock_settings, mock_session_cls, _le):
        mock_settings.return_value = _make_settings(census_acs_vintages=[2019])
        session = _mock_session()
        mock_session_cls.return_value = session

        compute_subdivision_demographics()

        session.add_all.assert_not_called()


# -- verify_acs_demographics tests -------------------------------------------


class TestVerifyAcsDemographics:
    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_success(self, mock_settings, mock_session_cls):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        # Return non-zero counts for all queries
        session.execute.return_value.scalar.return_value = 100
        mock_session_cls.return_value = session

        verify_acs_demographics()  # should not raise
        session.close.assert_called_once()

    @patch("pricepoint.data.geospatial.census_demographics.SessionLocal")
    @patch("pricepoint.data.geospatial.census_demographics.get_settings")
    def test_empty_table_raises(self, mock_settings, mock_session_cls):
        mock_settings.return_value = _make_settings()
        session = _mock_session()
        # First call (total count) returns 0
        result_mock = MagicMock()
        result_mock.scalar.return_value = 0
        session.execute.return_value = result_mock
        mock_session_cls.return_value = session

        with pytest.raises(RuntimeError, match="No records found"):
            verify_acs_demographics()
