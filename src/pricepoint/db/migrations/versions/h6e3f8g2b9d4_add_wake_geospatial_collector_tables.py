"""Add wake geospatial collector tables

Revision ID: h6e3f8g2b9d4
Revises: g5d2e7f1a8c3
Create Date: 2026-02-18 18:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h6e3f8g2b9d4"
down_revision: str | None = "g5d2e7f1a8c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _geom(geometry_type: str) -> geoalchemy2.types.Geometry:
    return geoalchemy2.types.Geometry(
        geometry_type=geometry_type,
        srid=4326,
        from_text="ST_GeomFromEWKT",
        name="geometry",
    )


def _loaded_at() -> sa.Column:
    return sa.Column(
        "loaded_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=True,
    )


def upgrade() -> None:
    # -- wake_farmers_markets --
    op.create_table(
        "wake_farmers_markets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("location_desc", sa.String(), nullable=True),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("active_day", sa.String(), nullable=True),
        sa.Column("months", sa.String(), nullable=True),
        sa.Column("hours", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("geom", _geom("POINT"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_farmers_markets_objectid", "wake_farmers_markets", ["objectid"])
    op.create_index("ix_wake_farmers_markets_name", "wake_farmers_markets", ["name"])

    # -- wake_libraries --
    op.create_table(
        "wake_libraries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("facility_type", sa.String(), nullable=True),
        sa.Column("hours_mt", sa.String(), nullable=True),
        sa.Column("hours_fri", sa.String(), nullable=True),
        sa.Column("hours_sat", sa.String(), nullable=True),
        sa.Column("hours_sun", sa.String(), nullable=True),
        sa.Column("geom", _geom("POINT"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_libraries_objectid", "wake_libraries", ["objectid"])
    op.create_index("ix_wake_libraries_name", "wake_libraries", ["name"])

    # -- wake_hospitals --
    op.create_table(
        "wake_hospitals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("facility", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("acute_care", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("telephone", sa.String(), nullable=True),
        sa.Column("gis_edit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("geom", _geom("POINT"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_hospitals_objectid", "wake_hospitals", ["objectid"])
    op.create_index("ix_wake_hospitals_facility", "wake_hospitals", ["facility"])

    # -- wake_parks --
    op.create_table(
        "wake_parks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("acres", sa.Float(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("park_type", sa.String(), nullable=True),
        sa.Column("manager", sa.String(), nullable=True),
        sa.Column("comments", sa.String(), nullable=True),
        sa.Column("corridor", sa.String(), nullable=True),
        sa.Column("os_number", sa.String(), nullable=True),
        sa.Column("created_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_edited_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("geom", _geom("MULTIPOLYGON"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_parks_objectid", "wake_parks", ["objectid"])
    op.create_index("ix_wake_parks_name", "wake_parks", ["name"])

    # -- raleigh_parks --
    op.create_table(
        "raleigh_parks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("park_type", sa.String(), nullable=True),
        sa.Column("developed", sa.String(), nullable=True),
        sa.Column("map_acres", sa.Float(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("zip_code", sa.String(), nullable=True),
        sa.Column("park_id", sa.String(), nullable=True),
        sa.Column("initial_acquisition_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("geom", _geom("MULTIPOLYGON"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raleigh_parks_objectid", "raleigh_parks", ["objectid"])
    op.create_index("ix_raleigh_parks_name", "raleigh_parks", ["name"])

    # -- cary_parks --
    op.create_table(
        "cary_parks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("facility_id", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("park_area", sa.Float(), nullable=True),
        sa.Column("park_url", sa.String(), nullable=True),
        sa.Column("num_parking", sa.Integer(), nullable=True),
        sa.Column("restroom", sa.String(), nullable=True),
        sa.Column("ada_compliant", sa.String(), nullable=True),
        sa.Column("camping", sa.String(), nullable=True),
        sa.Column("swimming", sa.String(), nullable=True),
        sa.Column("hiking", sa.String(), nullable=True),
        sa.Column("fishing", sa.String(), nullable=True),
        sa.Column("picnic", sa.String(), nullable=True),
        sa.Column("boating", sa.String(), nullable=True),
        sa.Column("road_cycle", sa.String(), nullable=True),
        sa.Column("mtb_cycle", sa.String(), nullable=True),
        sa.Column("playground", sa.String(), nullable=True),
        sa.Column("golf", sa.String(), nullable=True),
        sa.Column("soccer", sa.String(), nullable=True),
        sa.Column("baseball", sa.String(), nullable=True),
        sa.Column("basketball", sa.String(), nullable=True),
        sa.Column("skatepark", sa.String(), nullable=True),
        sa.Column("tennis_court", sa.String(), nullable=True),
        sa.Column("volleyball", sa.String(), nullable=True),
        sa.Column("fitness_trail", sa.String(), nullable=True),
        sa.Column("nature_trail", sa.String(), nullable=True),
        sa.Column("trailhead", sa.String(), nullable=True),
        sa.Column("open_space", sa.String(), nullable=True),
        sa.Column("lake", sa.String(), nullable=True),
        sa.Column("amphitheater", sa.String(), nullable=True),
        sa.Column("dog_park", sa.String(), nullable=True),
        sa.Column("disc_golf", sa.String(), nullable=True),
        sa.Column("climbing_rocks", sa.String(), nullable=True),
        sa.Column("climbing_ropes", sa.String(), nullable=True),
        sa.Column("batting_cages", sa.String(), nullable=True),
        sa.Column("geom", _geom("POINT"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cary_parks_objectid", "cary_parks", ["objectid"])
    op.create_index("ix_cary_parks_name", "cary_parks", ["name"])

    # -- wake_greenways --
    op.create_table(
        "wake_greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("trail_name", sa.String(), nullable=True),
        sa.Column("corridor_name", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("trail_status", sa.String(), nullable=True),
        sa.Column("trail_surface", sa.String(), nullable=True),
        sa.Column("trail_class", sa.String(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("open_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_access", sa.String(), nullable=True),
        sa.Column("accessibility_status", sa.String(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_greenways_objectid", "wake_greenways", ["objectid"])
    op.create_index("ix_wake_greenways_trail_name", "wake_greenways", ["trail_name"])

    # -- raleigh_greenways --
    op.create_table(
        "raleigh_greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("trail_name", sa.String(), nullable=True),
        sa.Column("greenway_type", sa.String(), nullable=True),
        sa.Column("location_desc", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("map_miles", sa.Float(), nullable=True),
        sa.Column("width_ft", sa.Float(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("ada", sa.String(), nullable=True),
        sa.Column("gw_status", sa.String(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raleigh_greenways_objectid", "raleigh_greenways", ["objectid"])
    op.create_index("ix_raleigh_greenways_trail_name", "raleigh_greenways", ["trail_name"])

    # -- cary_greenways --
    op.create_table(
        "cary_greenways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("segment", sa.String(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("trail_type", sa.String(), nullable=True),
        sa.Column("surface_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("install_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("open_to_public", sa.String(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cary_greenways_objectid", "cary_greenways", ["objectid"])
    op.create_index("ix_cary_greenways_name", "cary_greenways", ["name"])

    # -- wake_railroads --
    op.create_table(
        "wake_railroads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("branch_or", sa.String(), nullable=True),
        sa.Column("track_type", sa.String(), nullable=True),
        sa.Column("track_owner", sa.String(), nullable=True),
        sa.Column("shape_length", sa.Float(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_railroads_objectid", "wake_railroads", ["objectid"])

    # -- wake_major_roads --
    op.create_table(
        "wake_major_roads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("street_name", sa.String(), nullable=True),
        sa.Column("street_type", sa.String(), nullable=True),
        sa.Column("dir_prefix", sa.String(), nullable=True),
        sa.Column("dir_suffix", sa.String(), nullable=True),
        sa.Column("state_road", sa.String(), nullable=True),
        sa.Column("carto_name", sa.String(), nullable=True),
        sa.Column("corporation", sa.String(), nullable=True),
        sa.Column("class_name", sa.String(), nullable=True),
        sa.Column("label_name", sa.String(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_major_roads_objectid", "wake_major_roads", ["objectid"])
    op.create_index("ix_wake_major_roads_street_name", "wake_major_roads", ["street_name"])

    # -- wake_highways --
    op.create_table(
        "wake_highways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("street_name", sa.String(), nullable=True),
        sa.Column("street_type", sa.String(), nullable=True),
        sa.Column("dir_prefix", sa.String(), nullable=True),
        sa.Column("dir_suffix", sa.String(), nullable=True),
        sa.Column("from_left", sa.Integer(), nullable=True),
        sa.Column("to_left", sa.Integer(), nullable=True),
        sa.Column("from_right", sa.Integer(), nullable=True),
        sa.Column("to_right", sa.Integer(), nullable=True),
        sa.Column("state_road", sa.String(), nullable=True),
        sa.Column("carto_name", sa.String(), nullable=True),
        sa.Column("corporation", sa.String(), nullable=True),
        sa.Column("class_name", sa.String(), nullable=True),
        sa.Column("label_name", sa.String(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_highways_objectid", "wake_highways", ["objectid"])
    op.create_index("ix_wake_highways_street_name", "wake_highways", ["street_name"])

    # -- wake_utility_easements --
    op.create_table(
        "wake_utility_easements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("objectid", sa.Integer(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("ftr_code", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("geom", _geom("MULTILINESTRING"), nullable=True),
        _loaded_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wake_utility_easements_objectid", "wake_utility_easements", ["objectid"])


_ALL_TABLES = [
    "wake_farmers_markets",
    "wake_libraries",
    "wake_hospitals",
    "wake_parks",
    "raleigh_parks",
    "cary_parks",
    "wake_greenways",
    "raleigh_greenways",
    "cary_greenways",
    "wake_railroads",
    "wake_major_roads",
    "wake_highways",
    "wake_utility_easements",
]

_INDEX_NAMES = [
    "ix_wake_farmers_markets_objectid",
    "ix_wake_farmers_markets_name",
    "ix_wake_libraries_objectid",
    "ix_wake_libraries_name",
    "ix_wake_hospitals_objectid",
    "ix_wake_hospitals_facility",
    "ix_wake_parks_objectid",
    "ix_wake_parks_name",
    "ix_raleigh_parks_objectid",
    "ix_raleigh_parks_name",
    "ix_cary_parks_objectid",
    "ix_cary_parks_name",
    "ix_wake_greenways_objectid",
    "ix_wake_greenways_trail_name",
    "ix_raleigh_greenways_objectid",
    "ix_raleigh_greenways_trail_name",
    "ix_cary_greenways_objectid",
    "ix_cary_greenways_name",
    "ix_wake_railroads_objectid",
    "ix_wake_major_roads_objectid",
    "ix_wake_major_roads_street_name",
    "ix_wake_highways_objectid",
    "ix_wake_highways_street_name",
    "ix_wake_utility_easements_objectid",
]


def downgrade() -> None:
    for idx_name in reversed(_INDEX_NAMES):
        table = "_".join(idx_name.replace("ix_", "").rsplit("_", 1)[0].split("_"))
        # Extract table name from index name pattern: ix_{table}_{column}
        for tbl in _ALL_TABLES:
            if idx_name.startswith(f"ix_{tbl}_"):
                table = tbl
                break
        op.drop_index(idx_name, table_name=table)
    for table in reversed(_ALL_TABLES):
        op.drop_table(table)
