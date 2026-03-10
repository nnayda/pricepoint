"""Add customization columns to saved_pois.

Adds user_category, marker_color, and marker_image_url nullable columns
to saved_pois for visual customization in the POI tab and settings page.

Revision ID: f1g3h5j7k9l1
Revises: e8f0a2b4c6d8
Create Date: 2026-03-10

"""

import sqlalchemy as sa
from alembic import op

revision = "f1g3h5j7k9l1"
down_revision = "e8f0a2b4c6d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("saved_pois", sa.Column("user_category", sa.String(), nullable=True))
    op.add_column("saved_pois", sa.Column("marker_color", sa.String(7), nullable=True))
    op.add_column("saved_pois", sa.Column("marker_image_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("saved_pois", "marker_image_url")
    op.drop_column("saved_pois", "marker_color")
    op.drop_column("saved_pois", "user_category")
