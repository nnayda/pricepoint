"""LLM photo quality scoring DAG.

Triggered by Dataset update from the description_quality_scoring DAG,
ensuring description scoring completes before photo scoring starts
to avoid Ollama model-switching overhead.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)

DESCRIPTION_SCORING_DATASET = Asset("description_scoring_complete")


@dag(
    dag_id="photo_quality_scoring",
    schedule=[DESCRIPTION_SCORING_DATASET],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "transform", "housing", "llm", "quality", "photos", "vision"],
)
def photo_quality_scoring():
    """Score Redfin listing photos using LLM vision analysis."""

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
        """Verify scoring completed without excessive errors and DB has records."""
        from pricepoint.data.housing.photo_scorer import verify_photo_scores

        total = result["scored"] + result["skipped"] + result["errors"]
        if total > 0 and result["errors"] / total > 0.5:
            raise RuntimeError(
                f"Too many errors: {result['errors']}/{total} "
                f"({result['errors'] / total:.0%}) failed"
            )
        verify_photo_scores()
        logger.info(
            "Verification passed: %d scored, %d skipped, %d errors",
            result["scored"],
            result["skipped"],
            result["errors"],
        )

    result = score_photos()
    verify_scoring(result)


photo_quality_scoring()
