"""Tests for structured logging configuration and request logging middleware."""

import json
import logging

from fastapi import FastAPI
from starlette.testclient import TestClient

from pricepoint.api.logging_config import JSONFormatter, RequestLoggingMiddleware, request_id_ctx


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with only the request logging middleware."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    async def _ping():
        return {"ok": True}

    return app


class TestRequestID:
    """Request ID generation and propagation."""

    def test_request_id_in_response_header(self) -> None:
        """Each response must contain a unique X-Request-ID header."""
        client = TestClient(_make_app())
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) == 32  # uuid4 hex

    def test_request_id_unique_per_request(self) -> None:
        """Consecutive requests must receive distinct request IDs."""
        client = TestClient(_make_app())
        r1 = client.get("/ping")
        r2 = client.get("/ping")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


class TestJSONFormatter:
    """JSONFormatter produces the expected structured output."""

    def test_json_format_fields(self) -> None:
        """Formatted output must contain timestamp, level, logger, message."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "hello world"
        assert "timestamp" in parsed

    def test_json_format_includes_request_id(self) -> None:
        """When a request_id is set in context, it appears in the JSON output."""
        token = request_id_ctx.set("abc123")
        try:
            formatter = JSONFormatter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="with id",
                args=None,
                exc_info=None,
            )
            parsed = json.loads(formatter.format(record))
            assert parsed["request_id"] == "abc123"
        finally:
            request_id_ctx.reset(token)

    def test_json_format_no_request_id_when_unset(self) -> None:
        """Without a request context, request_id must be absent."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="no id",
            args=None,
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert "request_id" not in parsed
