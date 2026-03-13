"""File upload endpoint for Redfin HTML listings."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse

from pricepoint.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


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
            # Ensure group read/write for Airflow (UID 50000) + NFS
            os.chmod(dest, 0o664)
            saved.append(f.filename)
            logger.info("Saved Redfin HTML: %s", dest)
        except Exception as exc:
            logger.exception("Failed to save %s", f.filename)
            errors.append(f"{f.filename}: {exc}")

    status = 200 if saved else 400
    return JSONResponse(
        status_code=status,
        content={"saved": saved, "errors": errors},
    )
