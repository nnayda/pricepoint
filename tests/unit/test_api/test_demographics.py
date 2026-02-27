"""Tests for the demographics endpoint."""

from unittest.mock import MagicMock

from pricepoint.api.routes.demographics import (
    build_context_data,
    consolidate_income,
    consolidate_race,
    estimate_age_split,
)

# ── Helper to build a mock AcsDemographic row ──


def _make_acs_row(
    *,
    acs_year: int = 2024,
    total_population: int = 10000,
    male_population: int = 4900,
    female_population: int = 5100,
    race_white: int = 7000,
    race_black: int = 1500,
    race_asian: int = 500,
    race_american_indian: int = 50,
    race_pacific_islander: int = 20,
    race_other: int = 100,
    race_two_or_more: int = 200,
    hispanic: int = 1200,
    not_hispanic: int = 8800,
    hispanic_total: int = 10000,
    total_households: int = 4000,
    median_household_income: int = 75000,
    median_home_value: int = 350000,
    housing_total_occupied: int = 3800,
    housing_owner_occupied: int = 2500,
    housing_renter_occupied: int = 1300,
    pop_under_18: int = 2200,
    pop_18_to_22: int = 600,
    pop_23_to_29: int = 900,
    pop_30_to_39: int = 1500,
    pop_40_to_49: int = 1400,
    pop_50_to_64: int = 1800,
    pop_65_plus: int = 1600,
    hh_income_under_10k: int = 200,
    hh_income_10k_to_15k: int = 100,
    hh_income_15k_to_20k: int = 150,
    hh_income_20k_to_25k: int = 150,
    hh_income_25k_to_30k: int = 200,
    hh_income_30k_to_35k: int = 200,
    hh_income_35k_to_40k: int = 150,
    hh_income_40k_to_45k: int = 150,
    hh_income_45k_to_50k: int = 200,
    hh_income_50k_to_60k: int = 300,
    hh_income_60k_to_75k: int = 400,
    hh_income_75k_to_100k: int = 500,
    hh_income_100k_to_125k: int = 400,
    hh_income_125k_to_150k: int = 300,
    hh_income_150k_to_200k: int = 200,
    hh_income_200k_plus: int = 100,
    median_age: float = 38.5,
) -> MagicMock:
    row = MagicMock()
    for attr, val in locals().items():
        if attr == "row":
            continue
        setattr(row, attr, val)
    return row


# ── consolidate_race tests ──


class TestConsolidateRace:
    def test_basic_race_consolidation(self):
        row = _make_acs_row()
        result = consolidate_race(row)
        labels = [r.label for r in result]
        assert labels == ["White", "Black", "Hispanic", "Asian", "Other"]
        total = sum(r.value for r in result)
        assert abs(total - 100.0) < 0.5  # Should normalize to ~100%

    def test_hispanic_overlap_reduces_white(self):
        row = _make_acs_row(
            total_population=1000,
            race_white=800,
            hispanic=200,
            not_hispanic=800,
        )
        result = consolidate_race(row)
        white_val = next(r.value for r in result if r.label == "White")
        # White should be reduced because of Hispanic overlap
        assert white_val < 80.0  # 800 * 0.8 = 640 → less than 80%

    def test_zero_population_returns_all_zeros(self):
        row = _make_acs_row(total_population=0)
        result = consolidate_race(row)
        assert all(r.value == 0 for r in result)

    def test_normalizes_to_100_percent(self):
        row = _make_acs_row()
        result = consolidate_race(row)
        total = sum(r.value for r in result)
        assert abs(total - 100.0) < 0.5


# ── consolidate_income tests ──


class TestConsolidateIncome:
    def test_basic_income_brackets(self):
        row = _make_acs_row()
        result = consolidate_income(row)
        labels = [b.label for b in result]
        assert labels == ["<$25k", "$25-50k", "$50-100k", "$100-150k", "$150-200k", "$200k+"]

    def test_sums_to_approximately_100(self):
        # Ensure bracket values sum to total_households for a clean 100%
        row = _make_acs_row(
            total_households=3700,
        )
        result = consolidate_income(row)
        total = sum(b.value for b in result)
        assert abs(total - 100.0) < 0.5

    def test_zero_households_returns_zeros(self):
        row = _make_acs_row(total_households=0)
        result = consolidate_income(row)
        assert all(b.value == 0 for b in result)

    def test_bracket_grouping(self):
        # Only put income in <$25k range
        row = _make_acs_row(
            total_households=100,
            hh_income_under_10k=25,
            hh_income_10k_to_15k=25,
            hh_income_15k_to_20k=25,
            hh_income_20k_to_25k=25,
            hh_income_25k_to_30k=0,
            hh_income_30k_to_35k=0,
            hh_income_35k_to_40k=0,
            hh_income_40k_to_45k=0,
            hh_income_45k_to_50k=0,
            hh_income_50k_to_60k=0,
            hh_income_60k_to_75k=0,
            hh_income_75k_to_100k=0,
            hh_income_100k_to_125k=0,
            hh_income_125k_to_150k=0,
            hh_income_150k_to_200k=0,
            hh_income_200k_plus=0,
        )
        result = consolidate_income(row)
        assert result[0].value == 100.0  # <$25k
        assert all(b.value == 0 for b in result[1:])

    def test_50_to_100_merged(self):
        """$50-100k bracket merges old $50-75k and $75-100k ranges."""
        row = _make_acs_row(
            total_households=100,
            hh_income_under_10k=0,
            hh_income_10k_to_15k=0,
            hh_income_15k_to_20k=0,
            hh_income_20k_to_25k=0,
            hh_income_25k_to_30k=0,
            hh_income_30k_to_35k=0,
            hh_income_35k_to_40k=0,
            hh_income_40k_to_45k=0,
            hh_income_45k_to_50k=0,
            hh_income_50k_to_60k=20,
            hh_income_60k_to_75k=30,
            hh_income_75k_to_100k=50,
            hh_income_100k_to_125k=0,
            hh_income_125k_to_150k=0,
            hh_income_150k_to_200k=0,
            hh_income_200k_plus=0,
        )
        result = consolidate_income(row)
        assert result[2].label == "$50-100k"
        assert result[2].value == 100.0

    def test_150_200_and_200_plus_split(self):
        """$150-200k and $200k+ are separate brackets."""
        row = _make_acs_row(
            total_households=100,
            hh_income_under_10k=0,
            hh_income_10k_to_15k=0,
            hh_income_15k_to_20k=0,
            hh_income_20k_to_25k=0,
            hh_income_25k_to_30k=0,
            hh_income_30k_to_35k=0,
            hh_income_35k_to_40k=0,
            hh_income_40k_to_45k=0,
            hh_income_45k_to_50k=0,
            hh_income_50k_to_60k=0,
            hh_income_60k_to_75k=0,
            hh_income_75k_to_100k=0,
            hh_income_100k_to_125k=0,
            hh_income_125k_to_150k=0,
            hh_income_150k_to_200k=60,
            hh_income_200k_plus=40,
        )
        result = consolidate_income(row)
        assert result[4].label == "$150-200k"
        assert result[4].value == 60.0
        assert result[5].label == "$200k+"
        assert result[5].value == 40.0


# ── estimate_age_split tests ──


class TestEstimateAgeSplit:
    def test_basic_age_split(self):
        row = _make_acs_row()
        result = estimate_age_split(row)
        assert len(result) == 7
        labels = [b.range for b in result]
        assert labels == ["<18", "18-22", "23-29", "30-39", "40-49", "50-64", "65+"]

    def test_male_female_ratio(self):
        row = _make_acs_row(
            total_population=1000,
            male_population=600,
            female_population=400,
            pop_under_18=1000,
            pop_18_to_22=0,
            pop_23_to_29=0,
            pop_30_to_39=0,
            pop_40_to_49=0,
            pop_50_to_64=0,
            pop_65_plus=0,
        )
        result = estimate_age_split(row)
        under18 = result[0]
        # Male should be 60% of 100%, female 40% of 100%
        assert abs(under18.male - 60.0) < 0.1
        assert abs(under18.female - 40.0) < 0.1

    def test_zero_population(self):
        row = _make_acs_row(total_population=0)
        result = estimate_age_split(row)
        assert all(b.male == 0 and b.female == 0 for b in result)


# ── build_context_data tests ──


class TestBuildContextData:
    def test_returns_none_for_empty_rows(self):
        assert build_context_data([]) is None

    def test_uses_latest_year_for_snapshot(self):
        old = _make_acs_row(acs_year=2019, total_population=5000, median_household_income=60000)
        new = _make_acs_row(acs_year=2024, total_population=8000, median_household_income=80000)
        result = build_context_data([old, new])
        assert result is not None
        assert result.population == 8000
        assert result.median_income == 80000

    def test_includes_all_vintages_in_trends(self):
        rows = [
            _make_acs_row(acs_year=2009, total_population=3000),
            _make_acs_row(acs_year=2014, total_population=4000),
            _make_acs_row(acs_year=2019, total_population=5000),
            _make_acs_row(acs_year=2024, total_population=6000),
        ]
        result = build_context_data(rows)
        assert result is not None
        assert len(result.population_trend) == 4
        years = [p.year for p in result.population_trend]
        assert years == [2009, 2014, 2019, 2024]

    def test_ownership_rate_division_by_zero(self):
        row = _make_acs_row(housing_total_occupied=0, housing_owner_occupied=0)
        result = build_context_data([row])
        assert result is not None
        assert result.home_ownership_rate == 0.0

    def test_single_row_works(self):
        row = _make_acs_row(acs_year=2024)
        result = build_context_data([row])
        assert result is not None
        assert len(result.population_trend) == 1
        assert result.population_trend[0].year == 2024

    def test_median_age_trend(self):
        rows = [
            _make_acs_row(acs_year=2019, median_age=34.5),
            _make_acs_row(acs_year=2024, median_age=36.8),
        ]
        result = build_context_data(rows)
        assert result is not None
        assert len(result.median_age_trend) == 2
        assert result.median_age_trend[0].year == 2019
        assert result.median_age_trend[0].median_age == 34.5
        assert result.median_age_trend[1].year == 2024
        assert result.median_age_trend[1].median_age == 36.8


# ── Route parameter validation tests ──


class TestDemographicsParams:
    def test_missing_lat_returns_422(self, client):
        resp = client.get("/api/demographics", params={"lon": -78.78})
        assert resp.status_code == 422

    def test_missing_lon_returns_422(self, client):
        resp = client.get("/api/demographics", params={"lat": 35.79})
        assert resp.status_code == 422

    def test_lat_out_of_range_returns_422(self, client):
        resp = client.get("/api/demographics", params={"lat": 91, "lon": -78.78})
        assert resp.status_code == 422

    def test_lon_out_of_range_returns_422(self, client):
        resp = client.get("/api/demographics", params={"lat": 35.79, "lon": 181})
        assert resp.status_code == 422


class TestDemographicsEmpty:
    def test_returns_empty_contexts_when_no_data(self, client):
        """Returns empty contexts when no geographies match."""
        resp = client.get("/api/demographics", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        data = resp.json()
        assert "contexts" in data
        assert "benchmarks" in data
        # All contexts should have zero populations
        for ctx_key in ("subdivision", "block_group", "neighborhood", "town", "county"):
            assert data["contexts"][ctx_key]["population"] == 0


class TestDemographicsWithData:
    def test_returns_populated_contexts(self, app):
        """Demographics endpoint returns data when geographies and ACS rows exist."""
        from fastapi.testclient import TestClient

        from pricepoint.api.dependencies import get_db

        mock_db = MagicMock()

        acs_row = _make_acs_row(acs_year=2024, total_population=12000)
        acs_row.geography_level = "tract"
        acs_row.geoid = "37183052403"

        state_row = _make_acs_row(acs_year=2024, total_population=10000000)
        state_row.geography_level = "state"
        state_row.geoid = "37"

        us_row = _make_acs_row(acs_year=2024, total_population=330000000)
        us_row.geography_level = "us"
        us_row.geoid = "1"

        call_count = 0

        def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()

            if call_count == 1:
                # Geo lookup — no precomputed data, fall through to ST_Contains
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 2:
                # Tract lookup
                result.scalar_one_or_none.return_value = "37183052403"
                return result
            elif call_count == 3:
                # County subdivision lookup
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 4:
                # Block group lookup
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 5:
                # County lookup
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 6:
                # Subdivision lookup
                result.scalar_one_or_none.return_value = None
                return result
            elif call_count == 7:
                # ACS demographics query
                result.scalars.return_value.all.return_value = [acs_row, state_row, us_row]
                return result
            else:
                result.scalar_one_or_none.return_value = None
                return result

        mock_db.execute = mock_execute

        def _override():
            yield mock_db

        app.dependency_overrides[get_db] = _override
        client = TestClient(app)

        resp = client.get("/api/demographics", params={"lat": 35.79, "lon": -78.78})
        assert resp.status_code == 200
        data = resp.json()

        # Neighborhood should have data (tract was found)
        assert data["contexts"]["neighborhood"]["population"] == 12000
        assert len(data["contexts"]["neighborhood"]["race_ethnicity"]) == 5

        # Other contexts should be empty (no match)
        assert data["contexts"]["town"]["population"] == 0
        assert data["contexts"]["subdivision"]["population"] == 0
        assert data["contexts"]["block_group"]["population"] == 0
        assert data["contexts"]["county"]["population"] == 0

        # Benchmarks
        assert data["benchmarks"]["national"]["population"] == 330000000
        assert data["benchmarks"]["state"]["population"] == 10000000

        app.dependency_overrides.clear()
