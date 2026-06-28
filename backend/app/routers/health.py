"""
健康检查路由
GET /api/health

加密模型下：LOCKED 态（引擎未建）时 db=locked（服务本身可用，仅待解锁）；
UNLOCKED 态正常探测数据库连通性。
"""
import logging

from fastapi import APIRouter
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict[str, str]:
    """
    健康检查接口，同时验证数据库连接是否正常。
    Docker healthcheck 和负载均衡探针使用。LOCKED 态返回 db=locked（非 error）。
    """
    from app.core import database, keyvault

    if not keyvault.is_unlocked() or database.SessionLocal is None:
        return {"status": "ok", "db": "locked"}

    try:
        with database.SessionLocal() as db:  # type: ignore[misc]
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("health check db error", extra={"error": str(exc)})
        db_status = "error"

    return {"status": "ok", "db": db_status}
