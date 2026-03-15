"""add_school_spatial_indexes

Revision ID: b9f3a7c2d1e5
Revises: 74d6d4a48980
Create Date: 2026-03-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "b9f3a7c2d1e5"
down_revision: str | None = "74d6d4a48980"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column, desired_name, legacy_name_or_none)
_INDEXES = [
    ("schools", "location", "ix_schools_location", "idx_schools_location"),
    ("school_districts", "geom", "ix_school_districts_geom", "idx_school_districts_geom"),
    ("nces_schools", "location", "ix_nces_schools_location", "idx_nces_schools_location"),
    ("redfin_listings", "location", "ix_redfin_listings_location", "idx_redfin_listings_location"),
]


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    for table, column, desired_name, legacy_name in _INDEXES:
        if _index_exists(legacy_name):
            # Index already exists under the legacy name — rename to match convention
            op.execute(text(f'ALTER INDEX "{legacy_name}" RENAME TO "{desired_name}"'))
        elif not _index_exists(desired_name):
            op.create_index(
                desired_name,
                table,
                [column],
                unique=False,
                postgresql_using="gist",
            )


def downgrade() -> None:
    for table, _column, desired_name, _legacy_name in reversed(_INDEXES):
        if _index_exists(desired_name):
            op.drop_index(desired_name, table_name=table, postgresql_using="gist")
