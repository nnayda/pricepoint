"""Add economic_indicators table

Revision ID: i7f4g9h3c0e5
Revises: h6e3f8g2b9d4
Create Date: 2026-02-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i7f4g9h3c0e5"
down_revision: str | None = "h6e3f8g2b9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "economic_indicators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.String(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "observation_date", name="uq_economic_series_date"),
    )
    op.create_index(
        "idx_economic_series_date",
        "economic_indicators",
        ["series_id", "observation_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_economic_series_date", table_name="economic_indicators")
    op.drop_table("economic_indicators")
