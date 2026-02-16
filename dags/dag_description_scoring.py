"""LLM description quality scoring DAG.

Triggered by Dataset update from the redfin_listing_transform DAG
when production listings are updated. Also manually triggerable.
"""

import logging
from datetime import datetime, timedelta

from airflow.sdk import Asset, dag, task

logger = logging.getLogger(__name__)

LISTINGS_DATASET = Asset("redfin_listings")


@dag(
    dag_id="description_quality_scoring",
    schedule=[LISTINGS_DATASET],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "pricepoint",
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["data", "transform", "housing", "llm", "quality"],
)
def description_quality_scoring():
    """Score Redfin listing descriptions using LLM quality analysis."""

    @task()
    def score_descriptions():
        """Run LLM quality scoring on all listing descriptions."""
        from pricepoint.data.housing.description_scorer import score_all_descriptions

        result = score_all_descriptions()
        logger.info(
            "Scoring complete: %d scored, %d skipped, %d errors",
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

    result = score_descriptions()
    verify_scoring(result)


description_quality_scoring()
