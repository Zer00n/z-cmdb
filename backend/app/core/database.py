"""
Database connection module
SQLAlchemy 2.0 style, SQLite WAL mode
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _get_engine():
    """Create SQLAlchemy engine, ensure the database directory exists, enable WAL mode"""
    db_path = settings.db_path
    # Ensure directory exists (cross-platform)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.APP_ENV == "development",
    )

    # Enable WAL mode for better concurrent read performance and crash safety
    @event.listens_for(engine, "connect")
    def set_wal_mode(dbapi_connection, connection_record):  # type: ignore[misc]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = _get_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp, replacing the deprecated datetime.utcnow()"""
    return datetime.now(timezone.utc)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency injection: get a database Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
