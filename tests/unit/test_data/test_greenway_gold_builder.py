"""Tests for greenway gold builder."""

from unittest.mock import MagicMock, patch

from pricepoint.data.geospatial.greenway_gold_builder import (
    augment_gold_record,
    build_greenways_gold,
    extract_cary_fields,
    extract_cary_name,
    extract_raleigh_fields,
    extract_raleigh_name,
    extract_wake_fields,
    extract_wake_name,
    normalize_cary_status,
    normalize_cary_surface,
    normalize_raleigh_status,
    normalize_raleigh_surface,
    normalize_wake_status,
    normalize_wake_surface,
)
from pricepoint.db.models import Greenway

# ---------------------------------------------------------------------------
# Surface normalisation — Wake
# ---------------------------------------------------------------------------


class TestNormalizeWakeSurface:
    def test_concrete(self):
        assert normalize_wake_surface("CONCRETE") == "Paved"

    def test_asphalt(self):
        assert normalize_wake_surface("ASPHALT") == "Paved"

    def test_imported_loose_material(self):
        assert normalize_wake_surface("IMPORTED LOOSE MATERIAL") == "Crushed Stone"

    def test_native_material(self):
        assert normalize_wake_surface("NATIVE MATERIAL") == "Natural"

    def test_chunk_wood(self):
        assert normalize_wake_surface("CHUNK WOOD") == "Natural"

    def test_none(self):
        assert normalize_wake_surface(None) == "Unknown"

    def test_unknown_value(self):
        assert normalize_wake_surface("GRAVEL") == "Unknown"

    def test_whitespace_stripped(self):
        assert normalize_wake_surface("  ASPHALT  ") == "Paved"


# ---------------------------------------------------------------------------
# Surface normalisation — Cary
# ---------------------------------------------------------------------------


class TestNormalizeCarySurface:
    def test_asphalt(self):
        assert normalize_cary_surface("Asphalt") == "Paved"

    def test_concrete(self):
        assert normalize_cary_surface("Concrete") == "Paved"

    def test_limestone(self):
        assert normalize_cary_surface("Limestone") == "Paved"

    def test_aggregate(self):
        assert normalize_cary_surface("Aggregate") == "Crushed Stone"

    def test_gravel(self):
        assert normalize_cary_surface("Gravel") == "Crushed Stone"

    def test_decking(self):
        assert normalize_cary_surface("Decking") == "Decking"

    def test_none(self):
        assert normalize_cary_surface(None) == "Unknown"

    def test_unknown_value(self):
        assert normalize_cary_surface("Dirt") == "Unknown"


# ---------------------------------------------------------------------------
# Surface normalisation — Raleigh
# ---------------------------------------------------------------------------


class TestNormalizeRaleighSurface:
    def test_asphalt(self):
        assert normalize_raleigh_surface("Asphalt") == "Paved"

    def test_concrete(self):
        assert normalize_raleigh_surface("Concrete") == "Paved"

    def test_brick(self):
        assert normalize_raleigh_surface("Brick") == "Paved"

    def test_metal(self):
        assert normalize_raleigh_surface("Metal") == "Paved"

    def test_ncdot_bridge(self):
        assert normalize_raleigh_surface("NCDOT Bridge") == "Paved"

    def test_gravel(self):
        assert normalize_raleigh_surface("Gravel") == "Crushed Stone"

    def test_natural(self):
        assert normalize_raleigh_surface("Natural") == "Natural"

    def test_steel_wood_decking(self):
        assert normalize_raleigh_surface("Steel - Wood Decking") == "Decking"

    def test_wood_decking(self):
        assert normalize_raleigh_surface("Wood Decking") == "Decking"

    def test_trex_decking(self):
        assert normalize_raleigh_surface("Trex Decking") == "Decking"

    def test_none(self):
        assert normalize_raleigh_surface(None) == "Unknown"

    def test_unknown_value(self):
        assert normalize_raleigh_surface("unknown") == "Unknown"


# ---------------------------------------------------------------------------
# Status normalisation
# ---------------------------------------------------------------------------


class TestNormalizeWakeStatus:
    def test_existing(self):
        assert normalize_wake_status("EXISTING") == "Existing"

    def test_existing_lowercase(self):
        assert normalize_wake_status("existing") == "Existing"

    def test_proposed(self):
        assert normalize_wake_status("PROPOSED") == "Proposed"

    def test_none(self):
        assert normalize_wake_status(None) == "Proposed"


class TestNormalizeCaryStatus:
    def test_existing(self):
        assert normalize_cary_status("Existing") == "Existing"

    def test_none(self):
        assert normalize_cary_status(None) == "Unknown"


class TestNormalizeRaleighStatus:
    def test_existing(self):
        assert normalize_raleigh_status("Existing", None) == "Existing"

    def test_maintenance(self):
        assert normalize_raleigh_status("Maintenance", None) == "Existing"

    def test_under_construction(self):
        assert normalize_raleigh_status("Under Construction", None) == "Proposed"

    def test_fallback_to_gw_status(self):
        assert normalize_raleigh_status(None, "Existing") == "Existing"

    def test_both_none(self):
        assert normalize_raleigh_status(None, None) == "Unknown"


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------


class TestExtractWakeName:
    def test_trail_name_preferred(self):
        row = MagicMock(trail_name="Trail A", corridor_name="Corridor B", subsegment_name="Seg C")
        assert extract_wake_name(row) == "Trail A"

    def test_corridor_fallback(self):
        row = MagicMock(trail_name=None, corridor_name="Corridor B", subsegment_name="Seg C")
        assert extract_wake_name(row) == "Corridor B"

    def test_subsegment_fallback(self):
        row = MagicMock(trail_name=None, corridor_name=None, subsegment_name="Seg C")
        assert extract_wake_name(row) == "Seg C"

    def test_all_none(self):
        row = MagicMock(trail_name=None, corridor_name=None, subsegment_name=None)
        assert extract_wake_name(row) is None


def _cary_mock(**kwargs):
    """Create a MagicMock for Cary rows, handling the special ``name`` attr."""
    name_val = kwargs.pop("name", None)
    m = MagicMock(**kwargs)
    m.name = name_val
    return m


class TestExtractCaryName:
    def test_name_preferred(self):
        row = _cary_mock(name="Greenway A", segment=None, loop_name=None, loop_trail=None)
        assert extract_cary_name(row) == "Greenway A"

    def test_segment_fallback(self):
        row = _cary_mock(name=None, segment="Seg 1", loop_name=None, loop_trail=None)
        assert extract_cary_name(row) == "Seg 1"

    def test_loop_name_fallback(self):
        row = _cary_mock(name=None, segment=None, loop_name="Loop A", loop_trail=None)
        assert extract_cary_name(row) == "Loop A"

    def test_loop_trail_fallback(self):
        row = _cary_mock(name=None, segment=None, loop_name=None, loop_trail="Trail X")
        assert extract_cary_name(row) == "Trail X"


class TestExtractRaleighName:
    def test_trail_name(self):
        row = MagicMock(trail_name="Neuse River Trail")
        assert extract_raleigh_name(row) == "Neuse River Trail"

    def test_none(self):
        row = MagicMock(trail_name=None)
        assert extract_raleigh_name(row) is None


# ---------------------------------------------------------------------------
# Full row extraction
# ---------------------------------------------------------------------------


class TestExtractWakeFields:
    def test_extracts_all_fields(self):
        row = MagicMock(
            id=42,
            trail_name="Walnut Creek",
            corridor_name=None,
            subsegment_name=None,
            trail_surface="ASPHALT",
            trail_status="EXISTING",
            length=1.5,
            width=10.0,
            geom="FAKE_GEOM",
        )
        result = extract_wake_fields(row)
        assert result["source"] == "staging_wake_greenways"
        assert result["source_id"] == 42
        assert result["name"] == "Walnut Creek"
        assert result["surface_type"] == "Paved"
        assert result["status"] == "Existing"
        assert result["length"] == 1.5
        assert result["width"] == 10.0
        assert result["geom"] == "FAKE_GEOM"


class TestExtractCaryFields:
    def test_extracts_all_fields(self):
        row = _cary_mock(
            id=7,
            name="White Oak",
            segment=None,
            loop_name=None,
            loop_trail=None,
            surface_type="Asphalt",
            status="Existing",
            length=2.3,
            width=8.0,
            geom="FAKE_GEOM",
        )
        result = extract_cary_fields(row)
        assert result["source"] == "staging_cary_greenways"
        assert result["source_id"] == 7
        assert result["name"] == "White Oak"
        assert result["surface_type"] == "Paved"
        assert result["status"] == "Existing"
        assert result["length"] == 2.3


class TestExtractRaleighFields:
    def test_extracts_all_fields(self):
        row = MagicMock(
            id=99,
            trail_name="Neuse River",
            material="Concrete",
            status="Existing",
            gw_status=None,
            map_miles=3.1,
            width_ft=12.0,
            geom="FAKE_GEOM",
        )
        result = extract_raleigh_fields(row)
        assert result["source"] == "staging_raleigh_greenways"
        assert result["source_id"] == 99
        assert result["name"] == "Neuse River"
        assert result["surface_type"] == "Paved"
        assert result["status"] == "Existing"
        assert result["length"] == 3.1
        assert result["width"] == 12.0


# ---------------------------------------------------------------------------
# Augmentation
# ---------------------------------------------------------------------------


class TestAugmentGoldRecord:
    def test_town_overwrites_non_null(self):
        gold = Greenway(
            name="Old Name", surface_type="Unknown", status="Proposed", length=1.0, width=8.0
        )
        town_fields = {
            "name": "New Name",
            "surface_type": "Paved",
            "status": "Existing",
            "length": 2.0,
            "width": 10.0,
        }
        augment_gold_record(gold, town_fields)
        assert gold.name == "New Name"
        assert gold.surface_type == "Paved"
        assert gold.status == "Existing"
        assert gold.length == 2.0
        assert gold.width == 10.0

    def test_preserves_gold_when_town_is_none(self):
        gold = Greenway(
            name="Keep Me", surface_type="Paved", status="Existing", length=1.0, width=8.0
        )
        town_fields = {
            "name": None,
            "surface_type": None,
            "status": None,
            "length": None,
            "width": None,
        }
        augment_gold_record(gold, town_fields)
        assert gold.name == "Keep Me"
        assert gold.surface_type == "Paved"
        assert gold.length == 1.0

    def test_partial_overwrite(self):
        gold = Greenway(
            name="Old", surface_type="Unknown", status="Proposed", length=1.0, width=None
        )
        town_fields = {
            "name": "New",
            "surface_type": None,
            "status": "Existing",
            "length": None,
            "width": 12.0,
        }
        augment_gold_record(gold, town_fields)
        assert gold.name == "New"
        assert gold.surface_type == "Unknown"  # preserved
        assert gold.status == "Existing"
        assert gold.length == 1.0  # preserved
        assert gold.width == 12.0

    def test_missing_field_in_dict(self):
        gold = Greenway(name="Keep", surface_type="Paved", status="Existing", length=1.0, width=8.0)
        town_fields: dict = {}
        augment_gold_record(gold, town_fields)
        assert gold.name == "Keep"


# ---------------------------------------------------------------------------
# Builder integration (mocked session)
# ---------------------------------------------------------------------------


class TestBuildGreenwaysGold:
    def _make_wake_row(self, id_: int = 1, name: str = "Wake Trail"):
        row = MagicMock()
        row.id = id_
        row.trail_name = name
        row.corridor_name = None
        row.subsegment_name = None
        row.trail_surface = "ASPHALT"
        row.trail_status = "EXISTING"
        row.length = 1.0
        row.width = 10.0
        row.geom = "FAKE_GEOM"
        return row

    def _make_cary_row(self, id_: int = 1, name: str = "Cary Trail"):
        row = MagicMock()
        row.id = id_
        row.name = name
        row.segment = None
        row.loop_name = None
        row.loop_trail = None
        row.surface_type = "Asphalt"
        row.status = "Existing"
        row.length = 2.0
        row.width = 8.0
        row.geom = "FAKE_GEOM_CARY"
        return row

    def _make_raleigh_row(self, id_: int = 1, name: str = "Raleigh Trail"):
        row = MagicMock()
        row.id = id_
        row.trail_name = name
        row.material = "Concrete"
        row.status = "Existing"
        row.gw_status = None
        row.map_miles = 3.0
        row.width_ft = 12.0
        row.geom = "FAKE_GEOM_RAL"
        return row

    @patch("pricepoint.data.geospatial.greenway_gold_builder._find_best_match")
    def test_wake_only_build(self, mock_match):
        """When only Wake data exists, all are inserted as gold records."""
        session = MagicMock()
        wake_rows = [self._make_wake_row(1), self._make_wake_row(2)]

        # session.execute(...).scalars().all() returns different lists per call
        scalars_mock = MagicMock()
        scalars_mock.all.side_effect = [wake_rows, [], []]
        session.execute.return_value.scalars.return_value = scalars_mock

        stats = build_greenways_gold(session)

        assert stats["wake_inserted"] == 2
        assert stats["cary_matched"] == 0
        assert stats["cary_new"] == 0
        assert stats["raleigh_matched"] == 0
        assert stats["raleigh_new"] == 0

    @patch("pricepoint.data.geospatial.greenway_gold_builder._find_best_match")
    def test_cary_matched_augments_gold(self, mock_match):
        """A Cary row that spatially matches a Wake gold record augments it."""
        session = MagicMock()
        wake_rows = [self._make_wake_row(1)]
        cary_rows = [self._make_cary_row(1)]

        gold_record = Greenway(
            id=100,
            source="staging_wake_greenways",
            source_id=1,
            name="Wake Trail",
            surface_type="Unknown",
            status="Proposed",
            length=1.0,
            width=10.0,
        )
        mock_match.return_value = gold_record

        scalars_mock = MagicMock()
        scalars_mock.all.side_effect = [wake_rows, cary_rows, []]
        session.execute.return_value.scalars.return_value = scalars_mock

        stats = build_greenways_gold(session)

        assert stats["cary_matched"] == 1
        assert stats["cary_new"] == 0
        # Gold record should have been augmented with Cary values
        assert gold_record.name == "Cary Trail"
        assert gold_record.surface_type == "Paved"

    @patch("pricepoint.data.geospatial.greenway_gold_builder._find_best_match")
    def test_unmatched_town_inserts_new(self, mock_match):
        """An unmatched Raleigh row is inserted as a new gold record."""
        session = MagicMock()
        wake_rows = [self._make_wake_row(1)]
        raleigh_rows = [self._make_raleigh_row(1)]

        mock_match.return_value = None

        scalars_mock = MagicMock()
        scalars_mock.all.side_effect = [wake_rows, [], raleigh_rows]
        session.execute.return_value.scalars.return_value = scalars_mock

        stats = build_greenways_gold(session)

        assert stats["raleigh_matched"] == 0
        assert stats["raleigh_new"] == 1
