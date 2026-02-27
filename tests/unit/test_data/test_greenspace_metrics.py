"""Tests for greenspace region metrics computation."""

from unittest.mock import MagicMock

import pytest

from pricepoint.data.geospatial.greenspace_metrics import (
    GEO_LEVEL_CONFIG,
    ZSCORE_PARENT_PREFIX,
    compute_base_metrics,
    compute_zscores,
    enrich_population,
    verify_metrics,
)


class _FakeRow:
    """Lightweight row that supports attribute access."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


# ---------------------------------------------------------------------------
# compute_base_metrics
# ---------------------------------------------------------------------------


class TestComputeBaseMetrics:
    def test_inserts_rows_for_each_tiger_region(self):
        """Should insert one GreenspaceRegionMetric per TIGER region."""
        session = MagicMock()
        fake_rows = [
            _FakeRow(
                geoid="37183050100",
                name="Block Group 1",
                park_count=3,
                trail_count=1,
                total_park_acres=45.5,
                total_trail_miles=2.3,
                greenspace_area_sqm=184000.0,
                region_land_area_sqm=5000000,
                greenspace_ratio=0.0368,
            ),
            _FakeRow(
                geoid="37183050200",
                name="Block Group 2",
                park_count=0,
                trail_count=0,
                total_park_acres=0,
                total_trail_miles=0,
                greenspace_area_sqm=0,
                region_land_area_sqm=3000000,
                greenspace_ratio=0.0,
            ),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = fake_rows
        session.execute.return_value = mock_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        count = compute_base_metrics(session, "block_group", "37", "183")

        assert count == 2
        session.bulk_save_objects.assert_called_once()
        objects = session.bulk_save_objects.call_args[0][0]
        assert len(objects) == 2
        assert objects[0].geo_level == "block_group"
        assert objects[0].geoid == "37183050100"
        assert objects[0].park_count == 3

    def test_deletes_existing_rows_before_insert(self):
        """Should delete old rows for the geo_level before inserting new ones."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result
        session.query.return_value.filter.return_value.delete.return_value = 5

        count = compute_base_metrics(session, "tract", "37", "183")

        assert count == 0
        session.query.return_value.filter.return_value.delete.assert_called_once()

    def test_handles_null_greenspace_ratio(self):
        """Rows with zero aland should get greenspace_ratio=None."""
        session = MagicMock()
        fake_rows = [
            _FakeRow(
                geoid="37183",
                name="Wake County",
                park_count=10,
                trail_count=5,
                total_park_acres=200.0,
                total_trail_miles=15.0,
                greenspace_area_sqm=800000.0,
                region_land_area_sqm=0,
                greenspace_ratio=None,
            ),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = fake_rows
        session.execute.return_value = mock_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        count = compute_base_metrics(session, "county", "37", "183")

        assert count == 1
        obj = session.bulk_save_objects.call_args[0][0][0]
        assert obj.greenspace_ratio is None

    def test_county_level_uses_only_state_fips(self):
        """County-level query should only filter by state_fips, not county_fips."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        compute_base_metrics(session, "county", "37", "183")

        # Check that execute was called with params containing state_fips
        # but not county_fips
        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["state_fips"] == "37"
        assert "county_fips" not in params

    def test_sub_county_level_uses_both_fips(self):
        """Sub-county levels should filter by both state and county FIPS."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        compute_base_metrics(session, "block_group", "37", "183")

        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["state_fips"] == "37"
        assert params["county_fips"] == "183"

    def test_rounds_numeric_values(self):
        """Should round acres, miles, and area to reasonable precision."""
        session = MagicMock()
        fake_rows = [
            _FakeRow(
                geoid="37183050100",
                name="BG 1",
                park_count=1,
                trail_count=1,
                total_park_acres=45.5678901,
                total_trail_miles=2.3456789,
                greenspace_area_sqm=184000.123456,
                region_land_area_sqm=5000000,
                greenspace_ratio=0.036800024691,
            ),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = fake_rows
        session.execute.return_value = mock_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        compute_base_metrics(session, "block_group", "37", "183")

        obj = session.bulk_save_objects.call_args[0][0][0]
        assert obj.total_park_acres == 45.57
        assert obj.total_trail_miles == 2.35
        assert obj.greenspace_area_sqm == 184000.12


# ---------------------------------------------------------------------------
# enrich_population
# ---------------------------------------------------------------------------


class TestEnrichPopulation:
    def test_updates_population_metrics(self):
        """Should execute UPDATE joining ACS demographics."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 15
        session.execute.return_value = mock_result

        count = enrich_population(session, "block_group")

        assert count == 15
        session.execute.assert_called_once()
        session.flush.assert_called_once()

    def test_passes_correct_geo_level_params(self):
        """Should pass geo_level and acs_level params to the SQL."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        enrich_population(session, "county_subdivision")

        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["geo_level"] == "county_subdivision"
        assert params["acs_level"] == "county_subdivision"

    def test_zero_population_returns_zero_count(self):
        """When no ACS data matches, rowcount should be 0."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        count = enrich_population(session, "tract")

        assert count == 0


# ---------------------------------------------------------------------------
# compute_zscores
# ---------------------------------------------------------------------------


class TestComputeZscores:
    def test_computes_zscores_for_geo_level(self):
        """Should execute z-score UPDATE for the given geo_level."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 10
        session.execute.return_value = mock_result

        count = compute_zscores(session, "block_group")

        assert count == 10
        session.execute.assert_called_once()
        session.flush.assert_called_once()

    def test_uses_correct_prefix_length(self):
        """SQL should use LEFT(geoid, N) with the correct prefix length."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 5
        session.execute.return_value = mock_result

        compute_zscores(session, "county")

        sql_text = str(session.execute.call_args[0][0].text)
        # County uses LEFT(geoid, 2) for state-level grouping
        assert "LEFT(geoid, 2)" in sql_text

    def test_block_group_uses_county_prefix(self):
        """Block group z-scores should partition by county (LEFT 5)."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 20
        session.execute.return_value = mock_result

        compute_zscores(session, "block_group")

        sql_text = str(session.execute.call_args[0][0].text)
        assert "LEFT(geoid, 5)" in sql_text

    def test_all_seven_zscore_columns_in_sql(self):
        """SQL should update all 7 z-score columns."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        compute_zscores(session, "tract")

        sql_text = str(session.execute.call_args[0][0].text)
        for col in [
            "greenspace_ratio_zscore",
            "park_count_zscore",
            "trail_count_zscore",
            "total_park_acres_zscore",
            "total_trail_miles_zscore",
            "parks_per_1k_zscore",
            "greenspace_acres_per_1k_zscore",
        ]:
            assert col in sql_text, f"Missing z-score column: {col}"


# ---------------------------------------------------------------------------
# verify_metrics
# ---------------------------------------------------------------------------


class TestVerifyMetrics:
    def test_passes_when_all_levels_have_rows_and_zscores(self):
        """Should not raise when all geo levels have data."""
        session = MagicMock()
        # Each geo level checked twice: count > 0, zscore_count > 0
        session.query.return_value.filter.return_value.count.return_value = 10

        verify_metrics(session)  # should not raise

    def test_fails_when_geo_level_has_no_rows(self):
        """Should raise AssertionError if any level has zero rows."""
        session = MagicMock()
        # First call returns 0 (no rows)
        session.query.return_value.filter.return_value.count.return_value = 0

        with pytest.raises(AssertionError, match="No greenspace_region_metrics rows"):
            verify_metrics(session)

    def test_fails_when_zscores_not_populated(self):
        """Should raise if rows exist but z-scores are all NULL."""
        session = MagicMock()
        # Use side_effect: first call returns count > 0, second returns 0 (no z-scores)
        session.query.return_value.filter.return_value.count.side_effect = [10, 0]

        with pytest.raises(AssertionError, match="No z-scores populated"):
            verify_metrics(session)


# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_geo_level_config_has_four_levels(self):
        """Should have block_group, tract, county_subdivision, county."""
        assert set(GEO_LEVEL_CONFIG.keys()) == {
            "block_group",
            "tract",
            "county_subdivision",
            "county",
        }

    def test_zscore_parent_prefix_matches_levels(self):
        """Z-score prefix config should match geo level config."""
        assert set(ZSCORE_PARENT_PREFIX.keys()) == set(GEO_LEVEL_CONFIG.keys())

    def test_county_prefix_is_state_level(self):
        """County z-scores should group by state (2-char prefix)."""
        assert ZSCORE_PARENT_PREFIX["county"] == 2

    def test_sub_county_prefix_is_county_level(self):
        """Sub-county z-scores should group by county (5-char prefix)."""
        for level in ["block_group", "tract", "county_subdivision"]:
            assert ZSCORE_PARENT_PREFIX[level] == 5
