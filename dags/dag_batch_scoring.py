"""DAG: Batch score all properties with the production ML model.

Triggered after model training completes or on-demand.
"""

from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task


@dag(
    dag_id="batch_scoring",
    description="Score all properties using the production ML model",
    schedule=[Asset("trained_model"), Asset("feature_matrix")],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    params={"force_rebuild": False},
    tags=["model", "scoring"],
)
def batch_scoring():
    @task(outlets=[Asset("batch_scores")])
    def score_properties(**context) -> int:
        """Load production model and score stale properties."""
        from pricepoint.db.engine import SessionLocal
        from pricepoint.models.inference import score_all_properties

        force = context["params"].get("force_rebuild", False)
        db = SessionLocal()
        try:
            count = score_all_properties(db, force_rebuild=force)
        finally:
            db.close()

        return count

    score_properties()


batch_scoring()
