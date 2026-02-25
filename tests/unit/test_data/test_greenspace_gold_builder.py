"""Tests for greenspace gold builder."""

from unittest.mock import MagicMock

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
    def test_inserts_allowed_types(self):
        session = MagicMock()
        rows = [
            _make_open_space_row(1, "Umstead Park", 5000.0, "PARK"),
            _make_open_space_row(2, "Falls Greenway", 120.0, "GREENWAY"),
        ]
        session.execute.return_value.scalars.return_value.all.return_value = rows

        stats = build_greenspaces_gold(session)

        assert stats["inserted"] == 2
        # 1 delete + 1 select = 2 execute calls
        assert session.execute.call_count == 2
        assert session.add.call_count == 2

    def test_returns_zero_when_no_matching_rows(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []

        stats = build_greenspaces_gold(session)

        assert stats["inserted"] == 0
        assert session.add.call_count == 0

    def test_title_cases_type_values(self):
        session = MagicMock()
        rows = [_make_open_space_row(1, "Test", 10.0, "OPEN SPACE")]
        session.execute.return_value.scalars.return_value.all.return_value = rows

        build_greenspaces_gold(session)

        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, Greenspace)
        assert added_obj.type == "Open Space"

    def test_sets_source_correctly(self):
        session = MagicMock()
        rows = [_make_open_space_row(1, "Test", 10.0, "PARK")]
        session.execute.return_value.scalars.return_value.all.return_value = rows

        build_greenspaces_gold(session)

        added_obj = session.add.call_args[0][0]
        assert added_obj.source == "staging_wake_open_space"
        assert added_obj.source_id == 1

    def test_maps_name_and_acres(self):
        session = MagicMock()
        rows = [_make_open_space_row(1, "Big Park", 42.5, "PARK")]
        session.execute.return_value.scalars.return_value.all.return_value = rows

        build_greenspaces_gold(session)

        added_obj = session.add.call_args[0][0]
        assert added_obj.name == "Big Park"
        assert added_obj.acres == 42.5

    def test_maps_geom(self):
        session = MagicMock()
        rows = [_make_open_space_row(1, "Test", 10.0, "PARK", "MY_GEOM")]
        session.execute.return_value.scalars.return_value.all.return_value = rows

        build_greenspaces_gold(session)

        added_obj = session.add.call_args[0][0]
        assert added_obj.geom == "MY_GEOM"

    def test_deletes_existing_before_insert(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []

        build_greenspaces_gold(session)

        # First execute call should be the delete
        assert session.execute.call_count == 2
        # flush called after delete and after inserts
        assert session.flush.call_count == 2

    def test_multiple_rows_all_inserted(self):
        session = MagicMock()
        rows = [
            _make_open_space_row(i, f"Space {i}", float(i * 10), "PARK")
            for i in range(5)
        ]
        session.execute.return_value.scalars.return_value.all.return_value = rows

        stats = build_greenspaces_gold(session)

        assert stats["inserted"] == 5
        assert session.add.call_count == 5
