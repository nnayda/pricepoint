"""Add places table.

Revision ID: w0x2y4z6a8b0
Revises: v9w1x3y5z7a9
Create Date: 2026-02-25

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision = "w0x2y4z6a8b0"
down_revision = "h1i2f3l4d5k6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("alternate_categories", JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("operating_status", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("postcode", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column("brand_wikidata", sa.String(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("social", sa.String(), nullable=True),
        sa.Column("source_dataset", sa.String(), nullable=True),
        sa.Column("source_record_id", sa.String(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_places_source_id", "places", ["source_id"])
    op.create_index("ix_places_geom", "places", ["geom"], postgresql_using="gist")
    op.create_index("ix_places_name", "places", ["name"])
    op.create_index("ix_places_category", "places", ["category"])
    op.create_index("ix_places_state", "places", ["state"])


def downgrade() -> None:
    op.drop_index("ix_places_state", table_name="places")
    op.drop_index("ix_places_category", table_name="places")
    op.drop_index("ix_places_name", table_name="places")
    op.drop_index("ix_places_geom", table_name="places", postgresql_using="gist")
    op.drop_index("ix_places_source_id", table_name="places")
    op.drop_table("places")
