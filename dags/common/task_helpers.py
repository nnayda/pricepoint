"""Shared Airflow task utilities."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_execution_date_str(logical_date: datetime) -> str:
    """Format the logical execution date as YYYY-MM-DD."""
    return logical_date.strftime("%Y-%m-%d")


def notify_on_failure(context: dict) -> None:
    """Callback invoked when a task fails — send alerts.

    Placeholder: integrate with Slack, PagerDuty, email, etc.
    """
    dag = context.get("dag")
    dag_id = dag.dag_id if dag else "unknown"
    ti = context.get("task_instance")
    task_id = ti.task_id if ti else "unknown"
    logger.error("ALERT: Task %s in DAG %s failed.", task_id, dag_id)
