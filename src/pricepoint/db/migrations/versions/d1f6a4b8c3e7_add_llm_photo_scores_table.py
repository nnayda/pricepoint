"""Add llm_photo_scores table

Revision ID: d1f6a4b8c3e7
Revises: c9e5f3a8b2d4
Create Date: 2026-02-16 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d1f6a4b8c3e7"
down_revision: str | None = "c9e5f3a8b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_photo_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("photos_hash", sa.String(length=64), nullable=False),
        sa.Column("visual_quality_score", sa.Integer(), nullable=True),
        sa.Column("visual_reasoning", sa.Text(), nullable=True),
        sa.Column(
            "detected_features",
            postgresql.JSON(),
            nullable=True,
        ),
        sa.Column("renovation_level", sa.String(), nullable=True),
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
            name="uq_llm_photo_score_listing_model",
        ),
    )
    op.create_index(
        "ix_llm_photo_scores_listing_id",
        "llm_photo_scores",
        ["listing_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_photo_scores_listing_id", table_name="llm_photo_scores")
    op.drop_table("llm_photo_scores")
