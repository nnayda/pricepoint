"""add_school_spatial_indexes

Revision ID: b9f3a7c2d1e5
Revises: 74d6d4a48980
Create Date: 2026-03-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9f3a7c2d1e5"
down_revision: str | None = "74d6d4a48980"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_schools_location",
        "schools",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_school_districts_geom",
        "school_districts",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_nces_schools_location",
        "nces_schools",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "ix_redfin_listings_location",
        "redfin_listings",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_redfin_listings_location",
        table_name="redfin_listings",
        postgresql_using="gist",
    )
    op.drop_index(
        "ix_nces_schools_location",
        table_name="nces_schools",
        postgresql_using="gist",
    )
    op.drop_index(
        "ix_school_districts_geom",
        table_name="school_districts",
        postgresql_using="gist",
    )
    op.drop_index(
        "ix_schools_location",
        table_name="schools",
        postgresql_using="gist",
    )
