"""DAG: Batch score all properties with the production ML model.

Triggered after model training completes or on-demand.
"""

from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="batch_scoring",
    description="Score all properties using the production ML model",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["model", "scoring"],
)
def batch_scoring():
    @task()
    def score_properties() -> int:
        """Load production model and score all properties."""
        from pricepoint.db.engine import SessionLocal
        from pricepoint.models.inference import score_all_properties

        db = SessionLocal()
        try:
            count = score_all_properties(db)
        finally:
            db.close()

        return count

    score_properties()


batch_scoring()
