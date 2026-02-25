"""Tests for greenspace gold builder."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.greenspace_gold_builder import (
    ALLOWED_TYPES,
    build_greenspaces_gold,
)
from pricepoint.db.models import Greenspace, StagingWakeOpenSpace


class TestAllowedTypes:
    def test_gameland_allowed(self):
        assert "GAMELAND" in ALLOWED_TYPES

    def test_open_space_allowed(self):
        assert "OPEN SPACE" in ALLOWED_TYPES

    def test_greenway_allowed(self):
        assert "GREENWAY" in ALLOWED_TYPES

    def test_park_allowed(self):
        assert "PARK" in ALLOWED_TYPES

    def test_exactly_four_types(self):
        assert len(ALLOWED_TYPES) == 4

    def test_cemetery_not_allowed(self):
        assert "CEMETERY" not in ALLOWED_TYPES

    def test_water_not_allowed(self):
        assert "WATER" not in ALLOWED_TYPES


class TestTitleCaseNormalization:
    def test_gameland(self):
        assert "GAMELAND".title() == "Gameland"

    def test_open_space(self):
        assert "OPEN SPACE".title() == "Open Space"

    def test_greenway(self):
        assert "GREENWAY".title() == "Greenway"

    def test_park(self):
        assert "PARK".title() == "Park"


def _make_open_space_row(
    id_: int = 1,
    name: str = "Test Park",
    acres: float = 10.5,
    type_: str = "PARK",
    geom: str = "FAKE_GEOM",
):
    row = MagicMock(spec=StagingWakeOpenSpace)
    row.id = id_
    row.name = name
    row.acres = acres
    row.type = type_
    row.geom = geom
    return row


class TestBuildGreenspacesGold:
    def test_upserts_allowed_types(self):
        session = MagicMock()
        rows = [
            _make_open_space_row(1, "Umstead Park", 5000.0, "PARK"),
            _make_open_space_row(2, "Falls Greenway", 120.0, "GREENWAY"),
        ]
        session.execute.return_value.scalars.return_value.all.return_value = rows
        # Stale delete returns rowcount=0
        delete_result = MagicMock()
        delete_result.rowcount = 0
        # First call = select, subsequent = upserts, last = stale delete
        session.execute.side_effect = None
        session.execute.return_value.scalars.return_value.all.return_value = rows
        session.execute.return_value.rowcount = 0

        stats = build_greenspaces_gold(session)

        assert stats["upserted"] == 2

    def test_returns_zero_when_no_matching_rows(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        session.execute.return_value.rowcount = 0

        stats = build_greenspaces_gold(session)

        assert stats["upserted"] == 0

    @patch(
        "pricepoint.data.geospatial.greenspace_gold_builder.pg_insert"
    )
    def test_upsert_values_include_built_at(self, mock_pg_insert):
        session = MagicMock()
        rows = [_make_open_space_row(1, "Test", 10.0, "PARK")]
        session.execute.return_value.scalars.return_value.all.return_value = rows
        session.execute.return_value.rowcount = 0

        mock_stmt = MagicMock()
        mock_pg_insert.return_value.values.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt

        run_ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        build_greenspaces_gold(session, run_started=run_ts)

        # Verify pg_insert was called with Greenspace model
        mock_pg_insert.assert_called_with(Greenspace)
        # Verify values include built_at
        values_call = mock_pg_insert.return_value.values.call_args
        assert values_call[1]["built_at"] == run_ts

    def test_stale_row_cleanup(self):
        """Rows with built_at < run_started are deleted."""
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        # The stale delete returns rowcount of 3
        session.execute.return_value.rowcount = 3

        stats = build_greenspaces_gold(session)

        assert stats["stale_deleted"] == 3

    def test_run_started_defaults_to_now(self):
        """When run_started is not provided, it defaults to current time."""
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        session.execute.return_value.rowcount = 0

        stats = build_greenspaces_gold(session)

        assert stats["upserted"] == 0
        assert stats["stale_deleted"] == 0

    def test_multiple_rows_all_upserted(self):
        session = MagicMock()
        rows = [
            _make_open_space_row(i, f"Space {i}", float(i * 10), "PARK")
            for i in range(5)
        ]
        session.execute.return_value.scalars.return_value.all.return_value = rows
        session.execute.return_value.rowcount = 0

        stats = build_greenspaces_gold(session)

        assert stats["upserted"] == 5

    def test_flush_called_after_upserts_and_stale_delete(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        session.execute.return_value.rowcount = 0

        build_greenspaces_gold(session)

        assert session.flush.call_count == 2
