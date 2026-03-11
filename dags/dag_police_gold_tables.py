"""DAG: Build gold-layer police_incidents table.

Auto-triggered DAG that consolidates Raleigh, Cary, and Morrisville staging
police incident data into a single gold table with UCR-standardized
crime groups and categories.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="police_gold_tables",
    description="Build gold police_incidents from staging sources with UCR mapping",
    schedule=[
        Asset("raleigh_police_incidents"),
        Asset("cary_police_incidents"),
        Asset("morrisville_police_incidents"),
    ],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "gold", "police"],
)
def police_gold_tables():
    @task()
    def build_police_gold():
        """Build gold police_incidents table from all staging sources."""
        from pricepoint.data.geospatial.police_gold_builder import (
            build_police_incidents_gold,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            count = build_police_incidents_gold(session)
            session.commit()
            logger.info("Built %d gold police incident records", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task(outlets=[Asset("police_incidents")])
    def verify_gold():
        """Verify gold police_incidents table has been populated."""
        from pricepoint.data.geospatial.police_gold_builder import (
            verify_police_incidents_gold,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            verify_police_incidents_gold(session)
        finally:
            session.close()

    build_police_gold() >> verify_gold()


police_gold_tables()
