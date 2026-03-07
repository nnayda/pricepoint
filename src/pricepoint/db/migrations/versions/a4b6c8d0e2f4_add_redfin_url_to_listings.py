"""add redfin_url to listings

Revision ID: a4b6c8d0e2f4
Revises: z3a5b7c9d1e3
Create Date: 2026-03-07

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "a4b6c8d0e2f4"
down_revision = "z3a5b7c9d1e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staging_redfin_listings", sa.Column("redfin_url", sa.String(), nullable=True))
    op.add_column("redfin_listings", sa.Column("redfin_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("redfin_listings", "redfin_url")
    op.drop_column("staging_redfin_listings", "redfin_url")
