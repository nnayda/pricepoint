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

    # Data is populated by the overture_places_collection DAG via
    # refresh_place_names(), not during migration — the places table
    # is too large (22 GB+) for an inline migration INSERT.


def downgrade() -> None:
    op.drop_table("place_names")
