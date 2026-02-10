"""Add NCES schools and school address

Revision ID: a7b3c5d9e1f0
Revises: f4c8d2e6a1b3
Create Date: 2026-02-10 14:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b3c5d9e1f0"
down_revision: str | None = "f4c8d2e6a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns to schools table
    op.add_column("schools", sa.Column("address", sa.String(), nullable=True))
    op.add_column("schools", sa.Column("nces_id", sa.String(), nullable=True))
    op.add_column(
        "schools",
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("false"), nullable=True),
    )
    op.create_index("ix_schools_nces_id", "schools", ["nces_id"])

    # Create nces_schools table
    op.create_table(
        "nces_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nces_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("school_type", sa.String(), nullable=True),
        sa.Column("school_level", sa.String(), nullable=True),
        sa.Column("grades_low", sa.String(), nullable=True),
        sa.Column("grades_high", sa.String(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column("extras", sa.JSON(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nces_schools_nces_id", "nces_schools", ["nces_id"], unique=True)
    op.create_index(
        "idx_nces_schools_location",
        "nces_schools",
        ["location"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("idx_nces_schools_location", table_name="nces_schools")
    op.drop_index("ix_nces_schools_nces_id", table_name="nces_schools")
    op.drop_table("nces_schools")
    op.drop_index("ix_schools_nces_id", table_name="schools")
    op.drop_column("schools", "needs_review")
    op.drop_column("schools", "nces_id")
    op.drop_column("schools", "address")
