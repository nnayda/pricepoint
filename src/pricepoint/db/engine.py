"""SQLAlchemy engine and session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pricepoint.config.settings import get_settings

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Yield a database session, closing it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
