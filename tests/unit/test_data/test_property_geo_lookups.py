"""Tests for the property_geo_lookups builder module."""

from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.property_geo_lookups import (
    build_incremental,
    build_property_geo_lookups,
    verify_geo_lookups,
)


class TestBuildPropertyGeoLookups:
    """Tests for the full rebuild function."""

    def test_truncates_and_inserts(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 42

        count = build_property_geo_lookups(session)

        assert count == 42
        # Should execute TRUNCATE then the INSERT SQL
        assert session.execute.call_count == 2
        session.commit.assert_called_once()

    def test_returns_zero_for_empty_table(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 0

        count = build_property_geo_lookups(session)

        assert count == 0
        session.commit.assert_called_once()


class TestBuildIncremental:
    """Tests for the incremental update function."""

    def test_empty_property_ids_returns_zero(self):
        session = MagicMock()

        count = build_incremental(session, [])

        assert count == 0
        session.execute.assert_not_called()

    def test_deletes_then_inserts(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 3

        count = build_incremental(session, [1, 2, 3])

        assert count == 3
        # Should execute DELETE then INSERT
        assert session.execute.call_count == 2
        session.commit.assert_called_once()

    def test_passes_property_ids_to_queries(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 2
        ids = [10, 20]

        build_incremental(session, ids)

        # Both DELETE and INSERT should receive the property_ids
        for c in session.execute.call_args_list:
            args, kwargs = c
            if len(args) > 1:
                assert args[1]["property_ids"] == ids


class TestVerifyGeoLookups:
    """Tests for the verification function."""

    def test_full_coverage(self):
        session = MagicMock()
        # 9 scalar calls: total_props, total_lookups, tract, bg, noise, risk,
        # school_dist, park_dist, critical_risk
        session.scalar.side_effect = [100, 100, 95, 90, 10, 5, 80, 70, 3]

        stats = verify_geo_lookups(session)

        assert stats["total_properties"] == 100
        assert stats["total_lookups"] == 100
        assert stats["with_tract"] == 95
        assert stats["with_block_group"] == 90
        assert stats["in_noise_zone"] == 10
        assert stats["in_risk_zone"] == 5
        assert stats["with_school_dist"] == 80
        assert stats["with_park_dist"] == 70
        assert stats["in_critical_risk_zone"] == 3

    def test_coverage_gap_logs_warning(self):
        session = MagicMock()
        session.scalar.side_effect = [50, 40, 35, 30, 5, 2, 25, 20, 1]

        with patch("pricepoint.data.geospatial.property_geo_lookups.logger") as mock_logger:
            stats = verify_geo_lookups(session)

        assert stats["total_properties"] == 50
        assert stats["total_lookups"] == 40
        mock_logger.warning.assert_called_once()

    def test_handles_none_counts(self):
        session = MagicMock()
        session.scalar.side_effect = [None, None, None, None, None, None, None, None, None]

        stats = verify_geo_lookups(session)

        assert stats["total_properties"] == 0
        assert stats["total_lookups"] == 0
        assert stats["with_school_dist"] == 0
        assert stats["with_park_dist"] == 0
        assert stats["in_critical_risk_zone"] == 0
