"""add saved_poi alternate_names

Revision ID: a4b6c8d0e2f4
Revises: z3a5b7c9d1e3
Create Date: 2026-03-10 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b6c8d0e2f4"
down_revision: str | None = "z3a5b7c9d1e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "saved_pois",
        sa.Column(
            "alternate_names",
            sa.ARRAY(sa.String()),
            nullable=True,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("saved_pois", "alternate_names")
