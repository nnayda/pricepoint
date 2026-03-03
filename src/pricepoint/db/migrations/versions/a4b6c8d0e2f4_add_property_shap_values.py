"""Add property_shap_values table.

Revision ID: a4b6c8d0e2f4
Revises: z3a5b7c9d1e3
Create Date: 2026-03-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = "a4b6c8d0e2f4"
down_revision: str | None = "p6q8r0s2t4u6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "property_shap_values",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("redfin_listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("shap_values", JSON(), nullable=False),
        sa.Column("base_value", sa.Float(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_property_shap_values_property_id",
        "property_shap_values",
        ["property_id"],
    )
    op.create_unique_constraint(
        "uq_property_shap_prop_version",
        "property_shap_values",
        ["property_id", "model_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_property_shap_prop_version", "property_shap_values")
    op.drop_index("ix_property_shap_values_property_id", table_name="property_shap_values")
    op.drop_table("property_shap_values")
