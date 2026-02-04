"""DAG: Transform raw data into model-ready features.

Runs after data collection completes.
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.sensors.external_task import ExternalTaskSensor


@dag(
    dag_id="feature_engineering",
    description="Transform raw data into model-ready feature matrices",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["features", "engineering"],
)
def feature_engineering():
    wait_for_data = ExternalTaskSensor(
        task_id="wait_for_data_collection",
        external_dag_id="data_collection",
        external_task_id="validate_raw_data",
        timeout=3600,
        poke_interval=60,
    )

    @task()
    def build_geospatial_features():
        """Compute geospatial features."""
        raise NotImplementedError("Stub: implement geospatial feature engineering")

    @task()
    def build_housing_features():
        """Compute housing features."""
        raise NotImplementedError("Stub: implement housing feature engineering")

    @task()
    def build_economic_features():
        """Compute economic features."""
        raise NotImplementedError("Stub: implement economic feature engineering")

    @task()
    def assemble_feature_matrix():
        """Join all feature sets into a single training matrix."""
        raise NotImplementedError("Stub: implement feature assembly")

    geo = build_geospatial_features()
    housing = build_housing_features()
    econ = build_economic_features()
    assembly = assemble_feature_matrix()

    wait_for_data >> [geo, housing, econ]
    [geo, housing, econ] >> assembly


feature_engineering()
