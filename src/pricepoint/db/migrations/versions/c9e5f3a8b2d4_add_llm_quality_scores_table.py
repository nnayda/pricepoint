"""Add llm_quality_scores table

Revision ID: c9e5f3a8b2d4
Revises: b8d4f2a7c3e1
Create Date: 2026-02-16 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c9e5f3a8b2d4"
down_revision: str | None = "b8d4f2a7c3e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_quality_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("description_hash", sa.String(length=64), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("quality_reasoning", sa.Text(), nullable=True),
        sa.Column(
            "positive_factors",
            postgresql.JSON(),
            nullable=True,
        ),
        sa.Column(
            "negative_factors",
            postgresql.JSON(),
            nullable=True,
        ),
        sa.Column(
            "raw_response",
            postgresql.JSON(),
            nullable=False,
        ),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "listing_id",
            "model_name",
            "model_version",
            name="uq_llm_score_listing_model",
        ),
    )
    op.create_index(
        "ix_llm_quality_scores_listing_id",
        "llm_quality_scores",
        ["listing_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_quality_scores_listing_id", table_name="llm_quality_scores")
    op.drop_table("llm_quality_scores")
