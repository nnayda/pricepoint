"""DAG: Collect HIFLD infrastructure features.

Manual-trigger DAG that downloads cell towers, transmission lines, power plants,
natural gas pipelines, petroleum pipelines, and hospitals from HIFLD into PostGIS.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import dag, task

logger = logging.getLogger(__name__)


@dag(
    dag_id="hifld_infrastructure_collection",
    description="Load HIFLD infrastructure features into PostGIS",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "collection", "hifld", "infrastructure"],
)
def hifld_infrastructure_collection():
    @task()
    def fetch_cell_towers():
        """Fetch HIFLD cell tower features."""
        from pricepoint.data.geospatial.hifld_infrastructure import fetch_cell_towers

        fetch_cell_towers()

    @task()
    def verify_cell_towers():
        """Verify that cell tower records were loaded."""
        from pricepoint.data.geospatial.hifld_infrastructure import verify_cell_towers

        verify_cell_towers()

    @task()
    def fetch_transmission_lines():
        """Fetch HIFLD transmission line features."""
        from pricepoint.data.geospatial.hifld_infrastructure import fetch_transmission_lines

        fetch_transmission_lines()

    @task()
    def verify_transmission_lines():
        """Verify that transmission line records were loaded."""
        from pricepoint.data.geospatial.hifld_infrastructure import verify_transmission_lines

        verify_transmission_lines()

    @task()
    def fetch_power_plants():
        """Fetch HIFLD power plant features."""
        from pricepoint.data.geospatial.hifld_infrastructure import fetch_power_plants

        fetch_power_plants()

    @task()
    def verify_power_plants():
        """Verify that power plant records were loaded."""
        from pricepoint.data.geospatial.hifld_infrastructure import verify_power_plants

        verify_power_plants()

    @task()
    def fetch_nat_gas_pipelines():
        """Fetch HIFLD natural gas pipeline features."""
        from pricepoint.data.geospatial.hifld_infrastructure import fetch_nat_gas_pipelines

        fetch_nat_gas_pipelines()

    @task()
    def verify_nat_gas_pipelines():
        """Verify that natural gas pipeline records were loaded."""
        from pricepoint.data.geospatial.hifld_infrastructure import verify_nat_gas_pipelines

        verify_nat_gas_pipelines()

    @task()
    def fetch_petroleum_pipelines():
        """Fetch HIFLD petroleum pipeline features."""
        from pricepoint.data.geospatial.hifld_infrastructure import fetch_petroleum_pipelines

        fetch_petroleum_pipelines()

    @task()
    def verify_petroleum_pipelines():
        """Verify that petroleum pipeline records were loaded."""
        from pricepoint.data.geospatial.hifld_infrastructure import verify_petroleum_pipelines

        verify_petroleum_pipelines()

    @task()
    def fetch_hospitals():
        """Fetch HIFLD hospital features."""
        from pricepoint.data.geospatial.hifld_infrastructure import fetch_hospitals

        fetch_hospitals()

    @task()
    def verify_hospitals():
        """Verify that hospital records were loaded."""
        from pricepoint.data.geospatial.hifld_infrastructure import verify_hospitals

        verify_hospitals()

    fetch_cell_towers() >> verify_cell_towers()
    fetch_transmission_lines() >> verify_transmission_lines()
    fetch_power_plants() >> verify_power_plants()
    fetch_nat_gas_pipelines() >> verify_nat_gas_pipelines()
    fetch_petroleum_pipelines() >> verify_petroleum_pipelines()
    fetch_hospitals() >> verify_hospitals()


hifld_infrastructure_collection()
