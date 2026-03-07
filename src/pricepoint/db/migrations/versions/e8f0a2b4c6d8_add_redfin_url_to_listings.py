"""add redfin_url to listings

Revision ID: e8f0a2b4c6d8
Revises: d7e9f1a3b5c7
Create Date: 2026-03-07

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "e8f0a2b4c6d8"
down_revision = "d7e9f1a3b5c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staging_redfin_listings", sa.Column("redfin_url", sa.String(), nullable=True))
    op.add_column("redfin_listings", sa.Column("redfin_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("redfin_listings", "redfin_url")
    op.drop_column("staging_redfin_listings", "redfin_url")
