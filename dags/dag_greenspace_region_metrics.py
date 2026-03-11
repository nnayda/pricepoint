"""DAG: Precompute greenspace region metrics.

Computes park/trail counts, area ratios, population-normalised metrics,
and z-scores at four TIGER geographic levels (block_group, tract,
county_subdivision, county).  Manual trigger only.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="greenspace_region_metrics",
    description="Precompute greenspace metrics and z-scores at TIGER geographic levels",
    schedule=[
        Asset("greenspaces"),
        Asset("trails"),
        Asset("geo_boundaries"),
        Asset("demographics"),
    ],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "greenspace", "metrics"],
)
def greenspace_region_metrics():
    @task()
    def compute_block_groups():
        """Compute base metrics + population for block groups."""
        from pricepoint.config.settings import get_settings
        from pricepoint.data.geospatial.greenspace_metrics import (
            compute_base_metrics,
            enrich_population,
        )
        from pricepoint.db.engine import SessionLocal

        settings = get_settings()
        session = SessionLocal()
        try:
            count = compute_base_metrics(
                session, "block_group", settings.tiger_state_fips, settings.tiger_county_fips
            )
            enrich_population(session, "block_group")
            session.commit()
            logger.info("Block group metrics: %d rows", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def compute_tracts():
        """Compute base metrics + population for tracts."""
        from pricepoint.config.settings import get_settings
        from pricepoint.data.geospatial.greenspace_metrics import (
            compute_base_metrics,
            enrich_population,
        )
        from pricepoint.db.engine import SessionLocal

        settings = get_settings()
        session = SessionLocal()
        try:
            count = compute_base_metrics(
                session, "tract", settings.tiger_state_fips, settings.tiger_county_fips
            )
            enrich_population(session, "tract")
            session.commit()
            logger.info("Tract metrics: %d rows", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def compute_subdivisions():
        """Compute base metrics + population for county subdivisions."""
        from pricepoint.config.settings import get_settings
        from pricepoint.data.geospatial.greenspace_metrics import (
            compute_base_metrics,
            enrich_population,
        )
        from pricepoint.db.engine import SessionLocal

        settings = get_settings()
        session = SessionLocal()
        try:
            count = compute_base_metrics(
                session,
                "county_subdivision",
                settings.tiger_state_fips,
                settings.tiger_county_fips,
            )
            enrich_population(session, "county_subdivision")
            session.commit()
            logger.info("County subdivision metrics: %d rows", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def compute_counties():
        """Compute base metrics + population for counties."""
        from pricepoint.config.settings import get_settings
        from pricepoint.data.geospatial.greenspace_metrics import (
            compute_base_metrics,
            enrich_population,
        )
        from pricepoint.db.engine import SessionLocal

        settings = get_settings()
        session = SessionLocal()
        try:
            count = compute_base_metrics(
                session, "county", settings.tiger_state_fips, settings.tiger_county_fips
            )
            enrich_population(session, "county")
            session.commit()
            logger.info("County metrics: %d rows", count)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task()
    def compute_all_zscores():
        """Compute z-scores for all geo levels."""
        from pricepoint.data.geospatial.greenspace_metrics import (
            GEO_LEVEL_CONFIG,
            compute_zscores,
        )
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            for level in GEO_LEVEL_CONFIG:
                compute_zscores(session, level)
            session.commit()
            logger.info("Z-scores computed for all geo levels")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @task(outlets=[Asset("greenspace_metrics")])
    def verify():
        """Verify all metrics are populated."""
        from pricepoint.data.geospatial.greenspace_metrics import verify_metrics
        from pricepoint.db.engine import SessionLocal

        session = SessionLocal()
        try:
            verify_metrics(session)
        finally:
            session.close()

    base_tasks = [
        compute_block_groups(),
        compute_tracts(),
        compute_subdivisions(),
        compute_counties(),
    ]
    base_tasks >> compute_all_zscores() >> verify()


greenspace_region_metrics()
