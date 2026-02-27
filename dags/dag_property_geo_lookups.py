"""DAG: Build property geographic lookup table.

Auto-triggered after Redfin transform produces new listings.  Precomputes
geographic containment (census tract, block group, county subdivision, noise
zone, risk zone, school district) for every property with a location.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="property_geo_lookups",
    description="Precompute geographic containment lookups for properties",
    schedule=[Asset("redfin_listings")],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "gold", "geo"],
)
def property_geo_lookups():
    @task(outlets=[Asset("property_geo_lookups")])
    def build_lookups():
        """Full rebuild of property_geo_lookups table."""
        from pricepoint.data.geospatial.property_geo_lookups import (
            build_property_geo_lookups,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            count = build_property_geo_lookups(session)
            logger.info("Built %d property geo lookups", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def verify():
        """Verify lookup coverage."""
        from pricepoint.data.geospatial.property_geo_lookups import (
            verify_geo_lookups,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            stats = verify_geo_lookups(session)
            logger.info("Geo lookup verification: %s", stats)
        finally:
            session.close()

    build_lookups() >> verify()


property_geo_lookups()
