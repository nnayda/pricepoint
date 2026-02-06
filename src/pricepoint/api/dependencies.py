"""Shared FastAPI dependencies (DB session, model loader, etc.)."""

from collections.abc import AsyncIterator, Generator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from pricepoint.db.engine import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_valkey(request: Request) -> AsyncIterator[Redis | None]:
    """Yield a Valkey (Redis-compatible) connection from the app-level pool.

    Yields ``None`` when no pool has been configured so that callers can
    gracefully degrade when caching is unavailable.
    """
    pool: Redis | None = getattr(request.app.state, "valkey_pool", None)
    yield pool


def get_model():
    """Load the current production model from MLflow.

    Returns a callable prediction function.
    """
    raise NotImplementedError
