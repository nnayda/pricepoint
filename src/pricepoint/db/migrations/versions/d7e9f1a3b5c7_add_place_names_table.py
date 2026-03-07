"""Add place_names table for fast POI autocomplete.

Revision ID: d7e9f1a3b5c7
Revises: c6d8e0f2a4b6
Create Date: 2026-03-07
"""

import sqlalchemy as sa
from alembic import op

revision = "d7e9f1a3b5c7"
down_revision = "c6d8e0f2a4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "place_names",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("match_type", sa.String, nullable=False),
        sa.Column("value", sa.String, nullable=False),
        sa.Column("category", sa.String, nullable=True),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("match_type", "value", name="uq_place_name_type_value"),
    )

    op.create_index(
        "ix_place_names_value_trgm",
        "place_names",
        ["value"],
        postgresql_using="gin",
        postgresql_ops={"value": "gin_trgm_ops"},
    )

    # Populate with brands
    op.execute(
        """
        INSERT INTO place_names (match_type, value, category, count, refreshed_at)
        SELECT 'brand', brand_name, MIN(category), COUNT(*), NOW()
        FROM places
        WHERE brand_name IS NOT NULL
        GROUP BY brand_name
        """
    )

    # Populate with names (excluding values already inserted as brands)
    op.execute(
        """
        INSERT INTO place_names (match_type, value, category, count, refreshed_at)
        SELECT 'name', name, MIN(category), COUNT(*), NOW()
        FROM places
        WHERE name IS NOT NULL
          AND name NOT IN (SELECT value FROM place_names WHERE match_type = 'brand')
        GROUP BY name
        """
    )


def downgrade() -> None:
    op.drop_table("place_names")
