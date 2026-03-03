"""Add property_history_metrics table.

Revision ID: b5c7d9e1f3a5
Revises: b5c7d9e1f3g5
Create Date: 2026-03-03

"""

import sqlalchemy as sa
from alembic import op

revision = "b5c7d9e1f3a5"
down_revision = "b5c7d9e1f3g5"
branch_labels = None
depends_on = None

_TABLE = "property_history_metrics"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("township_geoid", sa.String(10), nullable=False),
        sa.Column("metric_month", sa.Date(), nullable=False),
        sa.Column("avg_days_on_market_1m", sa.Float(), nullable=True),
        sa.Column("avg_days_on_market_3m", sa.Float(), nullable=True),
        sa.Column("avg_days_on_market_1y", sa.Float(), nullable=True),
        sa.Column("median_sale_price_1m", sa.Float(), nullable=True),
        sa.Column("median_sale_price_3m", sa.Float(), nullable=True),
        sa.Column("median_sale_price_1y", sa.Float(), nullable=True),
        sa.Column("sample_count_1m", sa.Integer(), nullable=True),
        sa.Column("sample_count_3m", sa.Integer(), nullable=True),
        sa.Column("sample_count_1y", sa.Integer(), nullable=True),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("township_geoid", "metric_month", name="uq_phm_township_month"),
    )
    op.create_index("ix_phm_township", _TABLE, ["township_geoid"])
    op.create_index("ix_phm_month", _TABLE, ["metric_month"])


def downgrade() -> None:
    op.drop_index("ix_phm_month", table_name=_TABLE)
    op.drop_index("ix_phm_township", table_name=_TABLE)
    op.drop_table(_TABLE)
