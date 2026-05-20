"""
数据库连接模块
SQLAlchemy 2.0 风格，SQLite WAL 模式
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _get_engine():
    """创建 SQLAlchemy engine，确保数据库目录存在，开启 WAL 模式"""
    db_path = settings.db_path
    # 确保目录存在（跨平台）
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.APP_ENV == "development",
    )

    # 开启 WAL 模式，提高并发读性能，防止意外断电损坏
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
    """所有 SQLAlchemy 模型的基类"""
    pass


def utc_now() -> datetime:
    """timezone-aware UTC 时间戳，替代已弃用的 datetime.utcnow()"""
    return datetime.now(timezone.utc)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
