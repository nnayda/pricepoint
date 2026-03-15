"""Tests for greenspace region metrics computation."""

from unittest.mock import MagicMock, patch

import pytest

from pricepoint.data.geospatial.greenspace_metrics import (
    _COMMIT_INTERVAL,
    _VALIDATE_TABLES,
    BATCH_PREFIX_LEN,
    GEO_LEVEL_CONFIG,
    ZSCORE_PARENT_PREFIX,
    _compute_batch,
    compute_base_metrics,
    compute_zscores,
    enrich_population,
    validate_geometries,
    verify_metrics,
)


class _FakeRow:
    """Lightweight row that supports attribute access."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)


# ---------------------------------------------------------------------------
# validate_geometries
# ---------------------------------------------------------------------------


class TestValidateGeometries:
    def test_updates_all_six_tables(self):
        """Should run ST_MakeValid UPDATE on each table in _VALIDATE_TABLES."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        results = validate_geometries(session)

        assert len(results) == 6
        assert session.execute.call_count == 6
        for table, _dim in _VALIDATE_TABLES:
            assert table in results

    def test_commits_after_each_table(self):
        """Should commit once per table to persist fixes incrementally."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        validate_geometries(session)

        assert session.commit.call_count == 6

    def test_returns_fixed_counts(self):
        """Should return the number of rows fixed per table."""
        session = MagicMock()
        # Return different rowcounts for each table
        mock_results = []
        for count in [5, 0, 3, 0, 1, 0]:
            mr = MagicMock()
            mr.rowcount = count
            mock_results.append(mr)
        session.execute.side_effect = mock_results

        results = validate_geometries(session)

        assert results["greenspaces"] == 5
        assert results["trails"] == 0
        assert results["block_groups"] == 3
        assert results["tracts"] == 0
        assert results["townships"] == 1
        assert results["counties"] == 0

    def test_sql_wraps_with_collection_extract_and_multi(self):
        """SQL should wrap ST_MakeValid with ST_CollectionExtract+ST_Multi."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        validate_geometries(session)

        for c in session.execute.call_args_list:
            sql_text = str(c[0][0].text)
            assert "ST_Multi(ST_CollectionExtract(ST_MakeValid(geom)" in sql_text
            assert "ST_IsValid(geom)" in sql_text


# ---------------------------------------------------------------------------
# _compute_batch
# ---------------------------------------------------------------------------


class TestComputeBatch:
    def test_returns_metric_objects(self):
        """Should return GreenspaceRegionMetric objects for matching regions."""
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
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = fake_rows
        session.execute.return_value = mock_result

        result = _compute_batch(session, "block_group", "37183")

        assert len(result) == 1
        assert result[0].geo_level == "block_group"
        assert result[0].geoid == "37183050100"
        assert result[0].park_count == 3

    def test_passes_prefix_params(self):
        """Should pass prefix and prefix_len as query parameters."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        _compute_batch(session, "block_group", "37183")

        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["prefix"] == "37183"
        assert params["prefix_len"] == 5

    def test_sql_has_no_st_make_valid(self):
        """Query should not use ST_MakeValid — geometries pre-validated."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        _compute_batch(session, "block_group", "37183")

        sql_text = str(session.execute.call_args[0][0].text)
        assert "ST_MakeValid" not in sql_text

    def test_computes_intersection_once_in_parks_cte(self):
        """ST_Intersection should appear once in park_intersections CTE, not twice."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        _compute_batch(session, "block_group", "37183")

        sql_text = str(session.execute.call_args[0][0].text)
        # park_intersections CTE computes intersection once; parks CTE reuses it
        # The only ST_Intersection for parks should be in park_intersections
        park_section = sql_text.split("trail_metrics")[0]
        assert park_section.count("ST_Intersection") == 1

    def test_empty_batch_returns_empty_list(self):
        """When no regions match the prefix, should return empty list."""
        session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute.return_value = mock_result

        result = _compute_batch(session, "county", "99")

        assert result == []

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

        result = _compute_batch(session, "block_group", "37183")

        assert result[0].total_park_acres == 45.57
        assert result[0].total_trail_miles == 2.35
        assert result[0].greenspace_area_sqm == 184000.12


# ---------------------------------------------------------------------------
# compute_base_metrics
# ---------------------------------------------------------------------------


class TestComputeBaseMetrics:
    def test_queries_prefixes_and_batches(self):
        """Should query distinct prefixes then call _compute_batch per prefix."""
        session = MagicMock()
        prefix_rows = [_FakeRow(prefix="37183"), _FakeRow(prefix="37063")]
        prefix_result = MagicMock()
        prefix_result.fetchall.return_value = prefix_rows

        batch_result = MagicMock()
        batch_result.fetchall.return_value = [
            _FakeRow(
                geoid="37183050100",
                name="BG 1",
                park_count=1,
                trail_count=0,
                total_park_acres=10.0,
                total_trail_miles=0,
                greenspace_area_sqm=40000.0,
                region_land_area_sqm=5000000,
                greenspace_ratio=0.008,
            ),
        ]

        # First execute = prefix query, subsequent = batch queries
        session.execute.side_effect = [prefix_result, batch_result, batch_result]
        session.query.return_value.filter.return_value.delete.return_value = 0

        count = compute_base_metrics(session, "block_group")

        assert count == 2  # 1 row per batch × 2 batches

    def test_deletes_existing_rows_before_batching(self):
        """Should delete old rows for the geo_level before processing batches."""
        session = MagicMock()
        prefix_result = MagicMock()
        prefix_result.fetchall.return_value = []
        session.execute.return_value = prefix_result
        session.query.return_value.filter.return_value.delete.return_value = 5

        compute_base_metrics(session, "tract")

        session.query.return_value.filter.return_value.delete.assert_called_once()

    def test_commits_every_n_batches(self):
        """Should commit every _COMMIT_INTERVAL batches."""
        session = MagicMock()
        # Create enough prefixes to trigger at least one periodic commit
        prefix_rows = [_FakeRow(prefix=f"37{i:03d}") for i in range(_COMMIT_INTERVAL + 2)]
        prefix_result = MagicMock()
        prefix_result.fetchall.return_value = prefix_rows

        batch_result = MagicMock()
        batch_result.fetchall.return_value = []

        session.execute.side_effect = [prefix_result] + [batch_result] * len(prefix_rows)
        session.query.return_value.filter.return_value.delete.return_value = 0

        compute_base_metrics(session, "block_group")

        # Should commit at _COMMIT_INTERVAL + final commit for remaining
        assert session.commit.call_count == 2

    def test_empty_prefixes_returns_zero(self):
        """When TIGER table is empty, should return 0."""
        session = MagicMock()
        prefix_result = MagicMock()
        prefix_result.fetchall.return_value = []
        session.execute.return_value = prefix_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        count = compute_base_metrics(session, "county")

        assert count == 0

    @patch("pricepoint.data.geospatial.greenspace_metrics._compute_batch")
    def test_operational_error_skips_batch(self, mock_compute_batch):
        """OperationalError in a batch should skip it and continue."""
        from sqlalchemy.exc import OperationalError

        session = MagicMock()
        prefix_rows = [_FakeRow(prefix="37183"), _FakeRow(prefix="37063")]
        prefix_result = MagicMock()
        prefix_result.fetchall.return_value = prefix_rows
        session.execute.return_value = prefix_result
        session.query.return_value.filter.return_value.delete.return_value = 0

        # First batch fails, second succeeds
        mock_compute_batch.side_effect = [
            OperationalError("SSL EOF", None, None),
            [
                MagicMock(
                    geo_level="block_group",
                    geoid="37063050100",
                )
            ],
        ]

        # Should not raise
        compute_base_metrics(session, "block_group")

        # Should have rolled back after the error
        session.rollback.assert_called()


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

    def test_batch_prefix_matches_zscore_prefix(self):
        """Batch prefix lengths should match z-score prefix lengths."""
        assert BATCH_PREFIX_LEN == ZSCORE_PARENT_PREFIX

    def test_validate_tables_list(self):
        """Should validate all 6 source tables with correct geometry dimensions."""
        assert len(_VALIDATE_TABLES) == 6
        table_names = [t for t, _d in _VALIDATE_TABLES]
        assert "greenspaces" in table_names
        assert "trails" in table_names
        # trails are linestrings (dim 2), everything else is polygons (dim 3)
        for table, dim in _VALIDATE_TABLES:
            if table == "trails":
                assert dim == 2
            else:
                assert dim == 3

    def test_commit_interval_is_positive(self):
        """Commit interval should be a positive integer."""
        assert _COMMIT_INTERVAL > 0
