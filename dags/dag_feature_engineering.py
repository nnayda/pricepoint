"""DAG: Transform raw data into model-ready features."""

from datetime import datetime, timedelta

from airflow.sdk import dag, task


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

    @task()
    def build_geospatial():
        """Compute geospatial features."""
        import logging

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.geospatial import build_geospatial_features

        logger = logging.getLogger(__name__)
        db = SessionLocal()
        try:
            df = build_geospatial_features(db)
            logger.info("Geospatial features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def build_housing():
        """Compute housing features."""
        import logging

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.housing import build_housing_features

        logger = logging.getLogger(__name__)
        db = SessionLocal()
        try:
            df = build_housing_features(db)
            logger.info("Housing features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def build_economic():
        """Compute economic features."""
        import logging

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.economic import build_economic_features

        logger = logging.getLogger(__name__)
        db = SessionLocal()
        try:
            df = build_economic_features(db)
            logger.info("Economic features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def assemble_feature_matrix():
        """Join all feature sets into a single training matrix."""
        import logging

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.assembly import assemble_features

        logger = logging.getLogger(__name__)
        db = SessionLocal()
        try:
            df = assemble_features(db)
            logger.info("Assembled feature matrix shape: %s", df.shape)
        finally:
            db.close()

    geo = build_geospatial()
    housing = build_housing()
    econ = build_economic()
    assembly = assemble_feature_matrix()

    [geo, housing, econ] >> assembly


feature_engineering()
