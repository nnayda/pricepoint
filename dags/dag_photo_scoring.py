"""LLM photo quality scoring DAG.

Triggered by Dataset update from the redfin_listing_transform DAG
when production listings are updated. Waits for description scoring
to complete before running to avoid Ollama model-switching overhead.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task
from airflow.sensors.external_task import ExternalTaskSensor

logger = logging.getLogger(__name__)

LISTINGS_DATASET = Asset("redfin_listings")


@dag(
    dag_id="photo_quality_scoring",
    schedule=[LISTINGS_DATASET],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "transform", "housing", "llm", "quality", "photos"],
)
def photo_quality_scoring():
    """Score Redfin listing photos using LLM vision analysis."""

    wait_for_description_scoring = ExternalTaskSensor(
        task_id="wait_for_description_scoring",
        external_dag_id="description_quality_scoring",
        external_task_id=None,
        mode="reschedule",
        timeout=7200,
        poke_interval=60,
        allowed_states=["success"],
    )

    @task()
    def score_photos():
        """Run LLM photo scoring on all listing photos."""
        from pricepoint.data.housing.photo_scorer import score_all_photos

        result = score_all_photos()
        logger.info(
            "Photo scoring complete: %d scored, %d skipped, %d errors",
            result["scored"],
            result["skipped"],
            result["errors"],
        )
        return result

    @task()
    def verify_scoring(result):
        """Verify scoring completed without excessive errors."""
        total = result["scored"] + result["skipped"] + result["errors"]
        if total > 0 and result["errors"] / total > 0.5:
            raise RuntimeError(
                f"Too many errors: {result['errors']}/{total} "
                f"({result['errors'] / total:.0%}) failed"
            )
        logger.info(
            "Verification passed: %d scored, %d skipped, %d errors",
            result["scored"],
            result["skipped"],
            result["errors"],
        )

    result = score_photos()
    wait_for_description_scoring >> result
    verify_scoring(result)


photo_quality_scoring()
