"""File upload endpoint for Redfin HTML listings."""

import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse

from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


def _trigger_airflow_dag(dag_id: str) -> bool:
    """Trigger an Airflow DAG run via the REST API.

    Returns True if the DAG was triggered successfully, False otherwise.
    """
    settings = get_settings()
    base = settings.airflow_base_url.rstrip("/")

    # Authenticate to get a JWT token
    try:
        token_resp = httpx.post(
            f"{base}/auth/token",
            json={
                "username": settings.airflow_username,
                "password": settings.airflow_password,
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        token = token_resp.json()["access_token"]
    except Exception:
        logger.exception("Failed to authenticate with Airflow")
        return False

    # Trigger the DAG
    try:
        resp = httpx.post(
            f"{base}/api/v2/dags/{dag_id}/dagRuns",
            json={},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Triggered Airflow DAG %s: %s", dag_id, resp.json().get("dag_run_id"))
        return True
    except Exception:
        logger.exception("Failed to trigger Airflow DAG %s", dag_id)
        return False


@router.post("/upload/redfin")
async def upload_redfin_html(files: list[UploadFile]) -> JSONResponse:
    """Accept one or more Redfin HTML files and save to the configured directory."""
    settings = get_settings()
    dest_dir = Path(settings.redfin_html_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    errors: list[str] = []

    for f in files:
        if not f.filename:
            errors.append("File with no filename skipped")
            continue

        if not f.filename.endswith(".html"):
            errors.append(f"{f.filename}: only .html files are accepted")
            continue

        dest = dest_dir / f.filename
        try:
            content = await f.read()
            dest.write_bytes(content)
            saved.append(f.filename)
            logger.info("Saved Redfin HTML: %s", dest)
        except Exception as exc:
            logger.exception("Failed to save %s", f.filename)
            errors.append(f"{f.filename}: {exc}")

    # Trigger the collection DAG if any files were saved
    dag_triggered = False
    if saved:
        dag_triggered = _trigger_airflow_dag("redfin_listing_collection")

    status = 200 if saved else 400
    return JSONResponse(
        status_code=status,
        content={"saved": saved, "errors": errors, "dag_triggered": dag_triggered},
    )
