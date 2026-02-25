"""Add staging_places table.

Revision ID: x1y3z5a7b9c1
Revises: w0x2y4z6a8b0
Create Date: 2026-02-25

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision = "x1y3z5a7b9c1"
down_revision = "w0x2y4z6a8b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staging_places",
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
    )


def downgrade() -> None:
    op.drop_table("staging_places")
