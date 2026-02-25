"""DAG: Build risk boundary polygons around infrastructure.

Auto-triggered DAG that builds the gold ``risk_boundaries`` table with
pre-computed buffer polygons (critical + caution) around cell towers,
transmission lines, power plants, and pipelines.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="risk_boundary_build",
    description="Build risk boundary polygons around infrastructure",
    schedule=[
        Asset("cell_towers"),
        Asset("transmission_lines"),
        Asset("power_plants"),
        Asset("nat_gas_pipelines"),
        Asset("petroleum_pipelines"),
    ],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "gold", "infrastructure", "risk"],
)
def risk_boundary_build():
    @task()
    def build():
        """Build risk boundary polygons from infrastructure tables."""
        from pricepoint.data.geospatial.risk_boundaries import build_risk_boundaries
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            count = build_risk_boundaries(session)
            session.commit()
            logger.info("Built %d risk boundary records", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def verify():
        """Verify that risk boundaries were built."""
        from pricepoint.data.geospatial.risk_boundaries import verify_risk_boundaries
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            verify_risk_boundaries(session)
        finally:
            session.close()

    build() >> verify()


risk_boundary_build()
