"""
功能特性开关接口
GET /api/features   返回各功能域的启用状态（不受功能开关自身限制）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.services.config_service import is_cost_accounting_enabled

router = APIRouter(tags=["features"])


@router.get("/api/features")
def get_features(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """返回功能开关状态，供前端启动时决定渲染哪些入口"""
    return {
        "cost_accounting": is_cost_accounting_enabled(db),
    }
