"""DAG: Collect macroeconomic indicators from FRED API.

Weekly DAG that fetches mortgage rates, CPI, unemployment, housing starts,
and other economic time-series into the economic_indicators table.
"""

import logging
from datetime import datetime

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="economic_collection",
    description="Fetch macroeconomic indicators from the FRED API",
    schedule="@weekly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection", "economic", "fred"],
)
def economic_collection():
    @task()
    def fetch_indicators():
        """Fetch all configured FRED series incrementally."""
        from pricepoint.data.economic.macro_indicators import fetch_macro_indicators

        counts = fetch_macro_indicators()
        total = sum(counts.values())
        logger.info("Economic collection complete: %d new observations total", total)
        return counts

    fetch_indicators()


economic_collection()
