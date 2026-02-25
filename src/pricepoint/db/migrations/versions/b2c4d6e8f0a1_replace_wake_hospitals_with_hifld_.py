"""replace wake_hospitals with hifld hospitals

Revision ID: b2c4d6e8f0a1
Revises: a1b2c3d4e5f6
Create Date: 2026-02-25 00:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "b2c4d6e8f0a1"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_wake_hospitals_objectid", table_name="wake_hospitals")
    op.drop_index("ix_wake_hospitals_facility", table_name="wake_hospitals")
    op.drop_table("wake_hospitals")

    op.create_table(
        "hospitals",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("objectid", sa.Integer()),
        sa.Column("hifld_id", sa.String()),
        sa.Column("name", sa.String()),
        sa.Column("address", sa.String()),
        sa.Column("city", sa.String()),
        sa.Column("state", sa.String()),
        sa.Column("zip_code", sa.String()),
        sa.Column("telephone", sa.String()),
        sa.Column("hospital_type", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("population", sa.Integer()),
        sa.Column("county", sa.String()),
        sa.Column("countyfips", sa.String()),
        sa.Column("owner", sa.String()),
        sa.Column("beds", sa.Integer()),
        sa.Column("trauma", sa.String()),
        sa.Column("helipad", sa.String()),
        sa.Column("website", sa.String()),
        sa.Column("naics_code", sa.String()),
        sa.Column("naics_desc", sa.String()),
        sa.Column("ttl_staff", sa.Integer()),
        sa.Column("geom", Geometry("POINT", srid=4326)),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_hospitals_objectid", "hospitals", ["objectid"])
    op.create_index("ix_hospitals_hifld_id", "hospitals", ["hifld_id"])
    op.create_index("ix_hospitals_name", "hospitals", ["name"])
    op.create_index("ix_hospitals_geom", "hospitals", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_hospitals_geom", table_name="hospitals")
    op.drop_index("ix_hospitals_name", table_name="hospitals")
    op.drop_index("ix_hospitals_hifld_id", table_name="hospitals")
    op.drop_index("ix_hospitals_objectid", table_name="hospitals")
    op.drop_table("hospitals")

    op.create_table(
        "wake_hospitals",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("objectid", sa.Integer()),
        sa.Column("facility", sa.String()),
        sa.Column("address", sa.String()),
        sa.Column("city", sa.String()),
        sa.Column("acute_care", sa.String()),
        sa.Column("url", sa.String()),
        sa.Column("telephone", sa.String()),
        sa.Column("gis_edit_date", sa.DateTime(timezone=True)),
        sa.Column("geom", Geometry("POINT", srid=4326)),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_wake_hospitals_objectid", "wake_hospitals", ["objectid"])
    op.create_index("ix_wake_hospitals_facility", "wake_hospitals", ["facility"])
