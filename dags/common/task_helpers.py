"""Shared Airflow task utilities."""

from datetime import datetime


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
    print(f"ALERT: Task {task_id} in DAG {dag_id} failed.")
