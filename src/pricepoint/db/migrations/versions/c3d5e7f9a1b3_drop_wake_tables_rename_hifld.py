"""Drop Wake County tables and rename HIFLD tables.

Revision ID: c3d5e7f9a1b3
Revises: b2c4d6e8f0a1
Create Date: 2026-02-25 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3d5e7f9a1b3"
down_revision = "b2c4d6e8f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Drop 6 Wake County tables --
    op.drop_table("wake_farmers_markets")
    op.drop_table("wake_libraries")
    op.drop_table("wake_railroads")
    op.drop_table("wake_major_roads")
    op.drop_table("wake_highways")
    op.drop_table("wake_utility_easements")

    # -- Rename 5 HIFLD tables --
    op.rename_table("hifld_cell_towers", "cell_towers")
    op.rename_table("hifld_transmission_lines", "transmission_lines")
    op.rename_table("hifld_power_plants", "power_plants")
    op.rename_table("hifld_nat_gas_pipelines", "nat_gas_pipelines")
    op.rename_table("hifld_petroleum_pipelines", "petroleum_pipelines")

    # -- Rename indexes on renamed tables --
    op.execute("ALTER INDEX ix_hifld_cell_towers_geom RENAME TO ix_cell_towers_geom")
    op.execute("ALTER INDEX ix_hifld_cell_towers_objectid RENAME TO ix_cell_towers_objectid")
    op.execute("ALTER INDEX ix_hifld_transmission_lines_geom RENAME TO ix_transmission_lines_geom")
    op.execute(
        "ALTER INDEX ix_hifld_transmission_lines_objectid RENAME TO ix_transmission_lines_objectid"
    )
    op.execute("ALTER INDEX ix_hifld_power_plants_geom RENAME TO ix_power_plants_geom")
    op.execute("ALTER INDEX ix_hifld_power_plants_objectid RENAME TO ix_power_plants_objectid")
    op.execute("ALTER INDEX ix_hifld_nat_gas_pipelines_geom RENAME TO ix_nat_gas_pipelines_geom")
    op.execute(
        "ALTER INDEX ix_hifld_nat_gas_pipelines_objectid RENAME TO ix_nat_gas_pipelines_objectid"
    )
    op.execute(
        "ALTER INDEX ix_hifld_petroleum_pipelines_geom RENAME TO ix_petroleum_pipelines_geom"
    )
    op.execute(
        "ALTER INDEX ix_hifld_petroleum_pipelines_objectid"
        " RENAME TO ix_petroleum_pipelines_objectid"
    )
    op.execute("ALTER INDEX ix_hifld_power_plants_name RENAME TO ix_power_plants_name")


def downgrade() -> None:
    # -- Reverse index renames --
    op.execute("ALTER INDEX ix_power_plants_name RENAME TO ix_hifld_power_plants_name")
    op.execute(
        "ALTER INDEX ix_petroleum_pipelines_objectid"
        " RENAME TO ix_hifld_petroleum_pipelines_objectid"
    )
    op.execute(
        "ALTER INDEX ix_petroleum_pipelines_geom RENAME TO ix_hifld_petroleum_pipelines_geom"
    )
    op.execute(
        "ALTER INDEX ix_nat_gas_pipelines_objectid RENAME TO ix_hifld_nat_gas_pipelines_objectid"
    )
    op.execute("ALTER INDEX ix_nat_gas_pipelines_geom RENAME TO ix_hifld_nat_gas_pipelines_geom")
    op.execute("ALTER INDEX ix_power_plants_objectid RENAME TO ix_hifld_power_plants_objectid")
    op.execute("ALTER INDEX ix_power_plants_geom RENAME TO ix_hifld_power_plants_geom")
    op.execute(
        "ALTER INDEX ix_transmission_lines_objectid RENAME TO ix_hifld_transmission_lines_objectid"
    )
    op.execute("ALTER INDEX ix_transmission_lines_geom RENAME TO ix_hifld_transmission_lines_geom")
    op.execute("ALTER INDEX ix_cell_towers_objectid RENAME TO ix_hifld_cell_towers_objectid")
    op.execute("ALTER INDEX ix_cell_towers_geom RENAME TO ix_hifld_cell_towers_geom")

    # -- Reverse table renames --
    op.rename_table("petroleum_pipelines", "hifld_petroleum_pipelines")
    op.rename_table("nat_gas_pipelines", "hifld_nat_gas_pipelines")
    op.rename_table("power_plants", "hifld_power_plants")
    op.rename_table("transmission_lines", "hifld_transmission_lines")
    op.rename_table("cell_towers", "hifld_cell_towers")

    # -- Recreate dropped tables (simplified — schema only) --
    op.create_table(
        "wake_utility_easements",
        op.Column("id", op.sa.Integer(), primary_key=True, autoincrement=True),
        op.Column("objectid", op.sa.Integer(), index=True),
        op.Column("length", op.sa.Float()),
        op.Column("ftr_code", op.sa.String()),
        op.Column("status", op.sa.String()),
        op.Column("geom", op.sa.Text()),
        op.Column("loaded_at", op.sa.DateTime(timezone=True)),
    )
    op.create_table(
        "wake_highways",
        op.Column("id", op.sa.Integer(), primary_key=True, autoincrement=True),
        op.Column("objectid", op.sa.Integer(), index=True),
        op.Column("street_name", op.sa.String(), index=True),
        op.Column("geom", op.sa.Text()),
        op.Column("loaded_at", op.sa.DateTime(timezone=True)),
    )
    op.create_table(
        "wake_major_roads",
        op.Column("id", op.sa.Integer(), primary_key=True, autoincrement=True),
        op.Column("objectid", op.sa.Integer(), index=True),
        op.Column("street_name", op.sa.String(), index=True),
        op.Column("geom", op.sa.Text()),
        op.Column("loaded_at", op.sa.DateTime(timezone=True)),
    )
    op.create_table(
        "wake_railroads",
        op.Column("id", op.sa.Integer(), primary_key=True, autoincrement=True),
        op.Column("objectid", op.sa.Integer(), index=True),
        op.Column("geom", op.sa.Text()),
        op.Column("loaded_at", op.sa.DateTime(timezone=True)),
    )
    op.create_table(
        "wake_libraries",
        op.Column("id", op.sa.Integer(), primary_key=True, autoincrement=True),
        op.Column("objectid", op.sa.Integer(), index=True),
        op.Column("name", op.sa.String(), index=True),
        op.Column("geom", op.sa.Text()),
        op.Column("loaded_at", op.sa.DateTime(timezone=True)),
    )
    op.create_table(
        "wake_farmers_markets",
        op.Column("id", op.sa.Integer(), primary_key=True, autoincrement=True),
        op.Column("objectid", op.sa.Integer(), index=True),
        op.Column("name", op.sa.String(), index=True),
        op.Column("geom", op.sa.Text()),
        op.Column("loaded_at", op.sa.DateTime(timezone=True)),
    )
