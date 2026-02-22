"""Incremental school gold pipeline

Revision ID: p3r5t7v9x1z3
Revises: n2k9l4m8h5j0
Create Date: 2026-02-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p3r5t7v9x1z3"
down_revision: str | None = "n2k9l4m8h5j0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add schools_built_at to redfin_listings for dirty-property detection
    op.add_column(
        "redfin_listings",
        sa.Column("schools_built_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add updated_at to schools (gold)
    op.add_column(
        "schools",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    # Add updated_at to property_schools (gold)
    op.add_column(
        "property_schools",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    # Add missing GiST index on tiger_school_districts.geom
    op.create_index(
        "idx_tiger_school_districts_geom",
        "tiger_school_districts",
        ["geom"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("idx_tiger_school_districts_geom", table_name="tiger_school_districts")
    op.drop_column("property_schools", "updated_at")
    op.drop_column("schools", "updated_at")
    op.drop_column("redfin_listings", "schools_built_at")
