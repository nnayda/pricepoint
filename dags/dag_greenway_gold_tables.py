"""DAG: Build gold-layer greenways table.

Merges Wake, Cary, and Raleigh bronze greenway data into a single
deduplicated ``greenways`` gold table using spatial matching.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="greenway_gold_tables",
    description="Build gold greenways table from Wake + Cary + Raleigh bronze data",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "gold", "greenways"],
)
def greenway_gold_tables():
    @task()
    def build_greenways_gold():
        """Build gold greenways table from bronze sources."""
        from pricepoint.data.geospatial.greenway_gold_builder import (
            build_greenways_gold as _build,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            stats = _build(session)
            session.commit()
            logger.info("Greenway gold build stats: %s", stats)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def verify_gold():
        """Verify gold greenways table has been populated."""
        from sqlalchemy import func, select

        from pricepoint.db.engine import SessionLocal
        from pricepoint.db.models import Greenway

        session = SessionLocal()
        try:
            count = session.execute(
                select(func.count()).select_from(Greenway)
            ).scalar()
            if not count:
                raise RuntimeError("No records in gold greenways table after build")
            logger.info("Verified gold greenways table: %d records", count)
        finally:
            session.close()

    build_greenways_gold() >> verify_gold()


greenway_gold_tables()
