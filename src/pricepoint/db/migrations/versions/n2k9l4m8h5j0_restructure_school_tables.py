"""Restructure school tables into bronze/gold medallion architecture

Revision ID: n2k9l4m8h5j0
Revises: m1j8k3l7g4i9
Create Date: 2026-02-21 18:00:00.000000

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n2k9l4m8h5j0"
down_revision: str | None = "m1j8k3l7g4i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Bronze: rename existing tables ---
    op.rename_table("schools", "redfin_schools")
    op.rename_table("property_schools", "redfin_property_schools")

    # Drop columns no longer needed on redfin_schools (bronze)
    op.drop_index("ix_schools_nces_id", table_name="redfin_schools")
    op.drop_column("redfin_schools", "address")
    op.drop_column("redfin_schools", "nces_id")
    op.drop_column("redfin_schools", "needs_review")
    op.drop_column("redfin_schools", "location")

    # Rename school_id -> redfin_school_id on redfin_property_schools
    op.alter_column(
        "redfin_property_schools",
        "school_id",
        new_column_name="redfin_school_id",
    )

    # Drop columns from bronze linkage (moved to gold)
    op.drop_column("redfin_property_schools", "drive_minutes")
    op.drop_column("redfin_property_schools", "walk_minutes")
    op.drop_column("redfin_property_schools", "distance_miles")

    # Recreate unique index with new name and column
    op.drop_index("uq_property_school", table_name="redfin_property_schools")
    op.create_index(
        "uq_redfin_property_school",
        "redfin_property_schools",
        ["property_id", "redfin_school_id"],
        unique=True,
    )

    # --- Gold: create new schools table ---
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("nces_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("school_type", sa.String(), nullable=True),
        sa.Column("school_level", sa.String(), nullable=True),
        sa.Column("grades", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, from_text="ST_GeomFromEWKT"),
            nullable=True,
        ),
        sa.Column("enrollment", sa.Integer(), nullable=True),
        sa.Column("teachers", sa.Float(), nullable=True),
        sa.Column("student_teacher_ratio", sa.Float(), nullable=True),
        sa.Column("free_lunch_eligible", sa.Integer(), nullable=True),
        sa.Column("reduced_lunch_eligible", sa.Integer(), nullable=True),
        sa.Column("total_frl_eligible", sa.Integer(), nullable=True),
        sa.Column("pct_frl_eligible", sa.Float(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("nces_id", name="uq_schools_nces_id"),
    )
    op.create_index("ix_schools_nces_id", "schools", ["nces_id"])
    op.create_index("ix_schools_district_id", "schools", ["district_id"])
    op.create_index("idx_schools_location", "schools", ["location"], postgresql_using="gist")

    # --- Gold: create new property_schools table ---
    op.create_table(
        "property_schools",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column(
            "assigned",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
        sa.Column("distance_miles", sa.Float(), nullable=True),
        sa.Column("drive_minutes", sa.Integer(), nullable=True),
        sa.Column("walk_minutes", sa.Integer(), nullable=True),
    )
    op.create_index("ix_property_schools_property_id", "property_schools", ["property_id"])
    op.create_index("ix_property_schools_school_id", "property_schools", ["school_id"])
    op.create_index(
        "uq_property_school",
        "property_schools",
        ["property_id", "school_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop gold tables
    op.drop_index("uq_property_school", table_name="property_schools")
    op.drop_index("ix_property_schools_school_id", table_name="property_schools")
    op.drop_index("ix_property_schools_property_id", table_name="property_schools")
    op.drop_table("property_schools")

    op.drop_index("idx_schools_location", table_name="schools")
    op.drop_index("ix_schools_district_id", table_name="schools")
    op.drop_index("ix_schools_nces_id", table_name="schools")
    op.drop_table("schools")

    # Restore bronze -> original
    op.drop_index("uq_redfin_property_school", table_name="redfin_property_schools")

    op.add_column("redfin_property_schools", sa.Column("distance_miles", sa.Float(), nullable=True))
    op.add_column("redfin_property_schools", sa.Column("walk_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "redfin_property_schools",
        sa.Column("drive_minutes", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "redfin_property_schools",
        "redfin_school_id",
        new_column_name="school_id",
    )
    op.create_index(
        "uq_property_school",
        "redfin_property_schools",
        ["property_id", "school_id"],
        unique=True,
    )

    op.add_column(
        "redfin_schools",
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("false")),
    )
    op.add_column("redfin_schools", sa.Column("nces_id", sa.String(), nullable=True))
    op.add_column("redfin_schools", sa.Column("address", sa.String(), nullable=True))
    op.add_column(
        "redfin_schools",
        sa.Column(
            "location",
            geoalchemy2.Geometry("POINT", srid=4326, from_text="ST_GeomFromEWKT"),
            nullable=True,
        ),
    )
    op.create_index("ix_schools_nces_id", "redfin_schools", ["nces_id"])

    op.rename_table("redfin_property_schools", "property_schools")
    op.rename_table("redfin_schools", "schools")
