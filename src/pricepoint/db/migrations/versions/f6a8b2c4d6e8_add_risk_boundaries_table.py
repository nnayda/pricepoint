"""Add risk_boundaries table.

Revision ID: f6a8b2c4d6e8
Revises: e5f7a1b3c5d7
Create Date: 2026-02-25 00:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6a8b2c4d6e8"
down_revision = "e5f7a1b3c5d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_boundaries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("infrastructure_type", sa.String(), nullable=False),
        sa.Column("infrastructure_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="GEOMETRY",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "built_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_boundaries_geom", "risk_boundaries", ["geom"], postgresql_using="gist")
    op.create_index(
        "ix_risk_boundaries_infra",
        "risk_boundaries",
        ["infrastructure_type", "infrastructure_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_risk_boundaries_infra", table_name="risk_boundaries")
    op.drop_index("ix_risk_boundaries_geom", table_name="risk_boundaries", postgresql_using="gist")
    op.drop_table("risk_boundaries")
