"""add extracted_at to staging_redfin_listings

Revision ID: q1r3s5t7u9v1
Revises: f1g3h5j7k9l1
Create Date: 2026-03-10

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "q1r3s5t7u9v1"
down_revision = "f1g3h5j7k9l1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staging_redfin_listings", sa.Column("extracted_at", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("staging_redfin_listings", "extracted_at")
