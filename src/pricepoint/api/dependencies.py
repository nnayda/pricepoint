"""Shared FastAPI dependencies (DB session, model loader, etc.)."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from pricepoint.db.engine import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_model():
    """Load the current production model from MLflow.

    Returns a callable prediction function.
    """
    raise NotImplementedError
