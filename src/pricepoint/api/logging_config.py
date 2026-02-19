"""Structured logging configuration and request logging middleware."""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context variable that holds the current request ID.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach request_id when available.
        rid = request_id_ctx.get()
        if rid is not None:
            log_entry["request_id"] = rid

        # Propagate any extra keys the caller attached to the record.
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def setup_logging(level: str = "INFO", log_format: str = "json") -> None:
    """Configure the root logger.

    Parameters
    ----------
    level:
        Logging level name (DEBUG, INFO, WARNING, …).
    log_format:
        ``"json"`` for structured JSON output, ``"text"`` for human-readable.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove existing handlers to avoid duplicates when called multiple times.
    root.handlers.clear()

    handler = logging.StreamHandler()

    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))

    root.addHandler(handler)


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Generate a unique request ID and log request/response details."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = uuid.uuid4().hex
        request_id_ctx.set(rid)

        logger = logging.getLogger("pricepoint.api.access")
        logger.info("request started: %s %s", request.method, request.url.path)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        response.headers["X-Request-ID"] = rid

        logger.info(
            "request finished: %s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
