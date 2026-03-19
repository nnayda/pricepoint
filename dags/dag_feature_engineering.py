"""DAG: Transform raw data into model-ready features.

Triggered when all upstream assets update.  Resets dirty flags (since
the trigger means upstream data changed), detects stale properties, and
assembles features only for those properties.  Persists the result to
``property_features`` so downstream DAGs can read features without
recomputing.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, AssetAll, dag, task

FEATURES_READY = Asset("feature_matrix")
TRAINING_MATRIX_READY = Asset("training_feature_matrix")

logger = logging.getLogger(__name__)


@dag(
    dag_id="feature_engineering",
    description="Transform raw data into model-ready feature matrices",
    schedule=AssetAll(
        Asset("redfin_listings"),
        Asset("property_geo_lookups"),
        Asset("description_scores"),
        Asset("photo_scores"),
        Asset("schools"),
        Asset("property_history"),
    ),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    params={"force_rebuild": False},
    tags=["features", "engineering"],
)
def feature_engineering():

    @task()
    def reset_stale_flags(**context):
        """Null out features_built_at so all properties are reprocessed.

        Since this DAG is triggered by upstream asset changes, all
        properties need their features refreshed against the new data.
        Skipped when force_rebuild is True (redundant — all NULLs are
        already stale).
        """
        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.assembly import reset_features_built_at

        db = SessionLocal()
        try:
            count = reset_features_built_at(db)
            logger.info("Reset features_built_at for %d properties", count)
        finally:
            db.close()

    @task()
    def detect_stale(**context) -> list[int]:
        """Return property IDs that need feature recomputation."""
        force = context["params"].get("force_rebuild", False)

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.assembly import get_stale_property_ids

        db = SessionLocal()
        try:
            if force:
                # Force rebuild: return None-like sentinel — process all
                from sqlalchemy import select

                from pricepoint.db.models import RedfinListing

                ids = list(
                    db.execute(
                        select(RedfinListing.id).where(
                            RedfinListing.location.isnot(None),
                        )
                    )
                    .scalars()
                    .all()
                )
            else:
                ids = get_stale_property_ids(db)

            logger.info("Detected %d stale properties", len(ids))
            return ids
        finally:
            db.close()

    @task()
    def build_geospatial(property_ids: list[int]):
        """Compute geospatial features for stale properties."""
        if not property_ids:
            logger.info("No properties to process; skipping geospatial")
            return

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.geospatial import build_geospatial_features

        db = SessionLocal()
        try:
            df = build_geospatial_features(db, property_ids=property_ids)
            logger.info("Geospatial features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def build_housing(property_ids: list[int]):
        """Compute housing features for stale properties."""
        if not property_ids:
            logger.info("No properties to process; skipping housing")
            return

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.housing import build_housing_features

        db = SessionLocal()
        try:
            df = build_housing_features(db, property_ids=property_ids)
            logger.info("Housing features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def build_economic(property_ids: list[int]):
        """Compute economic features for stale properties."""
        if not property_ids:
            logger.info("No properties to process; skipping economic")
            return

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.economic import build_economic_features

        db = SessionLocal()
        try:
            df = build_economic_features(db, property_ids=property_ids)
            logger.info("Economic features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def build_comparables(property_ids: list[int]):
        """Compute comparable sales features for stale properties."""
        if not property_ids:
            logger.info("No properties to process; skipping comparables")
            return

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.comparables import build_comparable_features

        db = SessionLocal()
        try:
            df = build_comparable_features(db, property_ids=property_ids)
            logger.info("Comparable features shape: %s", df.shape)
        finally:
            db.close()

    @task()
    def assemble_feature_matrix(property_ids: list[int]):
        """Join all feature sets into a single training matrix and persist."""
        if not property_ids:
            logger.info("No stale properties; skipping assembly")
            return

        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.assembly import assemble_features
        from pricepoint.features.store import mark_features_built, save_feature_matrix

        db = SessionLocal()
        try:
            df = assemble_features(db, property_ids=property_ids)
            logger.info("Assembled feature matrix shape: %s", df.shape)
            saved = save_feature_matrix(db, df)
            logger.info("Persisted %d feature rows to property_features", saved)

            built_ids = df.index.tolist() if not df.empty else []
            if built_ids:
                mark_features_built(db, built_ids)
        finally:
            db.close()

    @task(outlets=[FEATURES_READY])
    def verify_matrix():
        """Verify feature matrix was persisted with expected row count."""
        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.store import load_feature_matrix

        db = SessionLocal()
        try:
            df = load_feature_matrix(db)
            if df.empty:
                raise RuntimeError("Feature matrix is empty after assembly")
            logger.info("Verified feature matrix: %d rows, %d cols", *df.shape)
        finally:
            db.close()

    @task(outlets=[TRAINING_MATRIX_READY])
    def assemble_training_matrix():
        """Build expanded training matrix (multi-sale records) and save as parquet to S3."""
        import io

        import boto3

        from pricepoint.config.settings import get_settings
        from pricepoint.db.engine import SessionLocal
        from pricepoint.features.assembly import assemble_training_features

        settings = get_settings()
        db = SessionLocal()
        try:
            df = assemble_training_features(db)
            if df.empty:
                logger.warning("Training matrix is empty; skipping S3 upload")
                return

            n_properties = df["property_id"].nunique()
            expansion = len(df) / n_properties if n_properties > 0 else 0
            logger.info(
                "Training matrix: %d rows, %d properties (%.1fx expansion)",
                len(df),
                n_properties,
                expansion,
            )

            # Save as parquet to MinIO/S3
            buf = io.BytesIO()
            df.to_parquet(buf, index=True, engine="pyarrow")
            buf.seek(0)

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            )
            key = "training/feature_matrix.parquet"
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=buf.getvalue(),
            )
            logger.info("Saved training matrix to s3://%s/%s", settings.s3_bucket, key)
        finally:
            db.close()

    reset = reset_stale_flags()
    stale_ids = detect_stale()
    geo = build_geospatial(stale_ids)
    housing = build_housing(stale_ids)
    econ = build_economic(stale_ids)
    comps = build_comparables(stale_ids)
    assembly = assemble_feature_matrix(stale_ids)
    verify = verify_matrix()
    training = assemble_training_matrix()

    reset >> stale_ids
    [geo, housing, econ, comps] >> assembly >> verify
    # Training matrix assembly runs after per-property features are built
    verify >> training


feature_engineering()
