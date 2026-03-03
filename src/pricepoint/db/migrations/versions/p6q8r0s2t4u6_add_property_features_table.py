"""Add property_features table for persisted feature matrix.

Revision ID: p6q8r0s2t4u6
Revises: m5n7p9q1r3s5
Create Date: 2026-03-03

"""

import sqlalchemy as sa
from alembic import op

revision = "p6q8r0s2t4u6"
down_revision = "m5n7p9q1r3s5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_features",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("redfin_listings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("features", sa.dialects.postgresql.JSON(), nullable=False),
        sa.Column("feature_hash", sa.String(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_property_features_property_id",
        "property_features",
        ["property_id"],
        unique=True,
    )
    op.create_index(
        "ix_property_features_computed_at",
        "property_features",
        ["computed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_property_features_computed_at", table_name="property_features")
    op.drop_index("ix_property_features_property_id", table_name="property_features")
    op.drop_table("property_features")
