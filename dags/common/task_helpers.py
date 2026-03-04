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


def send_ntfy_notification(
    topic: str,
    title: str,
    message: str,
    *,
    server_url: str = "https://ntfy.sh",
    priority: str = "default",
    tags: list[str] | None = None,
) -> bool:
    """Send a push notification via ntfy (best-effort, never raises).

    Uses ``urllib.request`` (stdlib) so no extra dependencies are needed
    inside the Airflow container.

    Returns ``True`` on success, ``False`` on failure.
    """
    import json
    import urllib.request

    url = f"{server_url.rstrip('/')}/{topic}"
    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "priority": priority,
    }
    if tags:
        payload["tags"] = tags

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            logger.info("ntfy notification sent (%s): %s", resp.status, title)
            return True
    except Exception:
        logger.warning("Failed to send ntfy notification", exc_info=True)
        return False
