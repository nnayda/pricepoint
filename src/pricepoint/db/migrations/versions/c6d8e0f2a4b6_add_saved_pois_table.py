"""Add saved_pois table and places.brand_name index.

Revision ID: c6d8e0f2a4b6
Revises: b5c7d9e1f3a5
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

revision = "c6d8e0f2a4b6"
down_revision = "b5c7d9e1f3a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_pois",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("match_type", sa.String, nullable=False),
        sa.Column("match_value", sa.String, nullable=False),
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("category", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "match_type", "match_value", name="uq_saved_poi_user_match"),
    )
    op.create_index("ix_places_brand_name", "places", ["brand_name"])


def downgrade() -> None:
    op.drop_index("ix_places_brand_name", table_name="places")
    op.drop_table("saved_pois")
