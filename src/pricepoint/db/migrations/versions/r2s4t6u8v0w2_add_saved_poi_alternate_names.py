"""add saved_poi alternate_names

Revision ID: r2s4t6u8v0w2
Revises: q1r3s5t7u9v1
Create Date: 2026-03-10 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r2s4t6u8v0w2"
down_revision: str | None = "q1r3s5t7u9v1"
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
