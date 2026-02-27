"""Add property_geo_lookups table.

Revision ID: k3l5m7n9p1q3
Revises: j2k4l6m8n0p2
Create Date: 2026-02-27

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision = "k3l5m7n9p1q3"
down_revision = "j2k4l6m8n0p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_geo_lookups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("census_tract_geoid", sa.String(length=11), nullable=True),
        sa.Column("census_block_group_geoid", sa.String(length=12), nullable=True),
        sa.Column("county_subdivision_geoid", sa.String(length=10), nullable=True),
        sa.Column("county_geoid", sa.String(length=5), nullable=True),
        sa.Column("subdivision_id", sa.Integer(), nullable=True),
        sa.Column("subdivision_name", sa.String(), nullable=True),
        sa.Column(
            "in_noise_zone",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("noise_max_db", sa.Integer(), nullable=True),
        sa.Column("noise_source_layers", JSON(), nullable=True),
        sa.Column(
            "in_risk_zone",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("risk_max_severity", sa.String(), nullable=True),
        sa.Column("risk_types", JSON(), nullable=True),
        sa.Column("school_district_geoid", sa.String(length=7), nullable=True),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["redfin_listings.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id"),
    )
    op.create_index(
        "ix_property_geo_lookups_property_id",
        "property_geo_lookups",
        ["property_id"],
    )
    op.create_index(
        "ix_property_geo_lookups_tract",
        "property_geo_lookups",
        ["census_tract_geoid"],
    )
    op.create_index(
        "ix_property_geo_lookups_bg",
        "property_geo_lookups",
        ["census_block_group_geoid"],
    )


def downgrade() -> None:
    op.drop_index("ix_property_geo_lookups_bg", table_name="property_geo_lookups")
    op.drop_index("ix_property_geo_lookups_tract", table_name="property_geo_lookups")
    op.drop_index("ix_property_geo_lookups_property_id", table_name="property_geo_lookups")
    op.drop_table("property_geo_lookups")
