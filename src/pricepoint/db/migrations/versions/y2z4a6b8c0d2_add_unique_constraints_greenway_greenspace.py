"""Add unique constraints on greenway and greenspace source keys.

Revision ID: y2z4a6b8c0d2
Revises: x1y3z5a7b9c1
Create Date: 2026-02-25

"""

from alembic import op

revision = "y2z4a6b8c0d2"
down_revision = "x1y3z5a7b9c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Replace regular index with unique constraint on greenways
    op.drop_index("ix_greenways_source_source_id", table_name="greenways")
    op.create_unique_constraint(
        "uq_greenways_source_source_id", "greenways", ["source", "source_id"]
    )

    # Replace regular index with unique constraint on greenspaces
    op.drop_index("ix_greenspaces_source_source_id", table_name="greenspaces")
    op.create_unique_constraint(
        "uq_greenspaces_source_source_id", "greenspaces", ["source", "source_id"]
    )


def downgrade() -> None:
    # Revert greenspaces: drop unique constraint, restore regular index
    op.drop_constraint("uq_greenspaces_source_source_id", "greenspaces", type_="unique")
    op.create_index(
        "ix_greenspaces_source_source_id", "greenspaces", ["source", "source_id"]
    )

    # Revert greenways: drop unique constraint, restore regular index
    op.drop_constraint("uq_greenways_source_source_id", "greenways", type_="unique")
    op.create_index(
        "ix_greenways_source_source_id", "greenways", ["source", "source_id"]
    )
