"""Add extra fields to staging wake and cary greenway tables.

Revision ID: t7u9v1w3x5y7
Revises: s6u8w0y2b4d6
Create Date: 2026-02-24

"""

import sqlalchemy as sa
from alembic import op

revision = "t7u9v1w3x5y7"
down_revision = "s6u8w0y2b4d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Wake greenways: trail_condition, slope, subsegment_name
    op.add_column("staging_wake_greenways", sa.Column("trail_condition", sa.String()))
    op.add_column("staging_wake_greenways", sa.Column("slope", sa.String()))
    op.add_column("staging_wake_greenways", sa.Column("subsegment_name", sa.String()))

    # Cary greenways: project_name, project_number, notes, loop_trail, loop_name,
    # official_cary_greenway_miles
    op.add_column("staging_cary_greenways", sa.Column("project_name", sa.String()))
    op.add_column("staging_cary_greenways", sa.Column("project_number", sa.String()))
    op.add_column("staging_cary_greenways", sa.Column("notes", sa.String()))
    op.add_column("staging_cary_greenways", sa.Column("loop_trail", sa.String()))
    op.add_column("staging_cary_greenways", sa.Column("loop_name", sa.String()))
    op.add_column(
        "staging_cary_greenways", sa.Column("official_cary_greenway_miles", sa.Float())
    )


def downgrade() -> None:
    # Cary greenways
    op.drop_column("staging_cary_greenways", "official_cary_greenway_miles")
    op.drop_column("staging_cary_greenways", "loop_name")
    op.drop_column("staging_cary_greenways", "loop_trail")
    op.drop_column("staging_cary_greenways", "notes")
    op.drop_column("staging_cary_greenways", "project_number")
    op.drop_column("staging_cary_greenways", "project_name")

    # Wake greenways
    op.drop_column("staging_wake_greenways", "subsegment_name")
    op.drop_column("staging_wake_greenways", "slope")
    op.drop_column("staging_wake_greenways", "trail_condition")
