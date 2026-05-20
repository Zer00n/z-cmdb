"""
pytest 全局 fixture
使用内存 SQLite（共享缓存模式），每个测试函数独立数据库
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker

# 必须在导入 app 之前设置，让 settings 读到 testing 环境
os.environ["APP_ENV"] = "testing"

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# 必须在 create_all 之前导入所有模型，否则表不会被创建
from app.models.user import User  # noqa: F401, E402
from app.models.asset import Asset, AssetPort  # noqa: F401, E402
from app.models.scan import ScanBatch, ScanSnapshotItem  # noqa: F401, E402
from app.models.audit import AuditLog  # noqa: F401, E402
from app.models.config import SystemConfig  # noqa: F401, E402
from app.models.topology import Topology  # noqa: F401, E402


@pytest.fixture(scope="function")
def db_engine():
    """
    每个测试函数创建独立的内存数据库。
    使用 StaticPool 确保所有连接共享同一个内存数据库实例。
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 关键：所有连接共享同一个底层连接
    )

    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine):
    """提供测试用 Session（用于纯 service/repo 层测试）"""
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    """
    提供 FastAPI TestClient。
    get_db 依赖覆盖为使用同一个测试 engine 的 Session。
    StaticPool 确保 TestClient 内部的请求和测试代码看到同一份数据。
    """
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False
    )

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db_from_client(db_engine):
    """
    给需要同时用 client 和 db 的测试提供 Session。
    与 client fixture 共享同一个 db_engine（StaticPool 保证同一内存 DB）。
    """
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
