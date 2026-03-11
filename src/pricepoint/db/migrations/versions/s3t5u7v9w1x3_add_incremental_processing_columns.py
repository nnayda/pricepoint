"""add incremental processing columns

Revision ID: s3t5u7v9w1x3
Revises: r2s4t6u8v0w2
Create Date: 2026-03-11 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "s3t5u7v9w1x3"
down_revision: str = "r2s4t6u8v0w2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Feature engineering dirty flag on redfin_listings
    op.add_column(
        "redfin_listings",
        sa.Column("features_built_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Staging processed flag
    op.add_column(
        "staging_redfin_listings",
        sa.Column(
            "is_processed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Mark all existing staging records as processed (already transformed)
    op.execute("UPDATE staging_redfin_listings SET is_processed = true")

    # Partial index for fast lookup of unprocessed staging records
    op.create_index(
        "ix_staging_unprocessed",
        "staging_redfin_listings",
        ["id"],
        postgresql_where=sa.text("is_processed = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_staging_unprocessed", table_name="staging_redfin_listings")
    op.drop_column("staging_redfin_listings", "is_processed")
    op.drop_column("redfin_listings", "features_built_at")
