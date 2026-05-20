"""
健康检查路由
GET /api/health
"""
import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict[str, str]:
    """
    健康检查接口，同时验证数据库连接是否正常。
    Docker healthcheck 和负载均衡探针使用。
    """
    # 验证数据库可达
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("health check db error", extra={"error": str(exc)})
        db_status = "error"

    return {"status": "ok", "db": db_status}
