"""
Database connection module — SQLCipher/MC 加密，引擎延迟初始化

加密模型下（PRD §6）：
  - import 期不再创建引擎，``engine`` 与 ``SessionLocal`` 初始为 ``None``；
  - 应用以 LOCKED 启动（keyvault），仅在 setup / 解锁成功后才调用
    :func:`init_engine` 用 DEK 构造加密引擎；
  - 迁移（alembic upgrade head）也移到解锁/setup 之后执行。

驱动：``apsw-sqlite3mc``（SQLite3 Multiple Ciphers）经 :mod:`app.core._apsw_dbapi`
DB-API 适配器接入 SQLAlchemy。``PRAGMA key`` 必须是连接上的第一条 SQL，因此在
creator 内设置，确保顺序（操作指南 §4）。
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

import apsw
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core import _apsw_dbapi, keyvault
from app.core.config import settings

# import 期为 None —— 解锁/setup 后由 init_engine 创建
_engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp, replacing the deprecated datetime.utcnow()"""
    return datetime.now(timezone.utc)


def init_engine(dek_hex: str, db_path: str | Path | None = None) -> Engine:
    """用 DEK 构造加密引擎并创建 SessionLocal。

    ``PRAGMA key`` 必须是每条连接的第一条 SQL（操作指南 §4），因此放在
    creator 里。随后设置 cipher 算法、WAL、外键。
    """
    global _engine, SessionLocal

    if not dek_hex:
        raise ValueError("DEK (hex) is required to init the encrypted engine")

    path = str(db_path) if db_path is not None else str(settings.db_path)
    # 确保目录存在（跨平台）
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    hexkey = dek_hex

    def _creator():
        conn = apsw.Connection(path)
        cur = conn.cursor()
        # 1) raw key 第一条（跳过 KDF，DEK 本就是随机 32 字节）
        cur.execute(f'PRAGMA key="x\'{hexkey}\'"')
        # 2) 显式 MC 算法 = sqlcipher（MC 默认即此，显式以求确定）
        cur.execute('PRAGMA cipher="sqlcipher"')
        # 3) WAL + 外键（SQLCipher/MC 兼容 WAL）
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
        return _apsw_dbapi.connect_apsw(conn)

    _engine = create_engine(
        "sqlite://",
        module=_apsw_dbapi,
        creator=_creator,
        echo=settings.APP_ENV == "development",
    )
    SessionLocal = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return _engine


def get_engine() -> Optional[Engine]:
    """返回当前引擎（未初始化为 None）。"""
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: get a database Session.

    LOCKED 态（SessionLocal 为 None）下调用是程序错误 —— 锁中间件会在路由
    之前就拦截返回 423，正常不会走到这里。此处兜底抛错以暴露问题。
    """
    if SessionLocal is None:
        raise RuntimeError("database is locked; unlock before accessing data")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def shutdown_engine() -> None:
    """释放引擎（lock / 进程退出时调用）。"""
    global _engine, SessionLocal
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:  # noqa: BLE001
            pass
    _engine = None
    SessionLocal = None
