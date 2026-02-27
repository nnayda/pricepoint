"""DAG: Collect raw data from all sources.

Runs daily to ingest geospatial, housing, and economic data.
"""

from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="data_collection",
    description="Collect raw data from geospatial, housing, and economic sources",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 0,
    },
    tags=["data", "collection"],
)
def data_collection():
    @task()
    def collect_police_incidents():
        """Fetch police incident data."""
        raise NotImplementedError("Stub: implement police incident collection")

    @task()
    def collect_nearby_features():
        """Fetch nearby POI features."""
        raise NotImplementedError("Stub: implement nearby feature collection")

    @task()
    def collect_schools():
        """Fetch school data."""
        raise NotImplementedError("Stub: implement school data collection")

    @task()
    def collect_capital_projects():
        """Fetch capital improvement project data."""
        raise NotImplementedError("Stub: implement capital project collection")

    @task()
    def collect_county_assessments():
        """Fetch county property assessments."""
        raise NotImplementedError("Stub: implement county assessment collection")

    @task()
    def collect_redfin_listings():
        """Fetch Redfin listing data."""
        raise NotImplementedError("Stub: implement Redfin listing collection")

    @task()
    def collect_macro_indicators():
        """Fetch macroeconomic indicators."""
        raise NotImplementedError("Stub: implement macro indicator collection")

    @task()
    def validate_raw_data():
        """Validate that all raw data landed successfully."""
        raise NotImplementedError("Stub: implement raw data validation")

    # Geospatial sources (parallel)
    geo_tasks = [
        collect_police_incidents(),
        collect_nearby_features(),
        collect_schools(),
        collect_capital_projects(),
    ]

    # Housing sources (parallel)
    housing_tasks = [
        collect_county_assessments(),
        collect_redfin_listings(),
    ]

    # Economic sources
    econ_tasks = [collect_macro_indicators()]

    # Validation runs after all collection tasks
    all_tasks = geo_tasks + housing_tasks + econ_tasks
    validate = validate_raw_data()
    for t in all_tasks:
        t >> validate


data_collection()
