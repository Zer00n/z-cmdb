"""
费率字典接口（受 require_cost_feature 守卫，仅 super_admin 可写）
GET /api/cost/rates   读取费率
PUT /api/cost/rates   更新费率
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, SuperAdminUser, RequireCostFeature
from app.repositories import cost_repo
from app.services import audit_service

router = APIRouter(prefix="/api/cost/rates", tags=["cost-rates"])


@router.get("")
def get_cost_rates(
    _feature: RequireCostFeature = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """读取所有费率配置"""
    rates = cost_repo.get_all_cost_rates(db)
    result = {}
    for r in rates:
        result[r.key] = {
            "value": r.value,
            "description": r.description,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    return result


@router.put("")
def update_cost_rates(
    body: dict,
    request: Request,
    _feature: RequireCostFeature = None,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """批量更新费率配置"""
    now = datetime.now(timezone.utc)
    updated = []
    for key, meta in body.items():
        value = meta.get("value") if isinstance(meta, dict) else meta
        description = meta.get("description") if isinstance(meta, dict) else None
        cost_repo.upsert_cost_rate(
            db, key=key,
            value=value if isinstance(value, str) else str(value),
            description=description,
            updated_by=current_user.id,
        )
        updated.append(key)

    audit_service.log_from_request(
        db, request, action_type="CONFIG", user=current_user,
        target_type="cost_rates",
        details={"updated_keys": updated},
    )
    db.commit()
    return {"message": f"已更新 {len(updated)} 项费率", "updated": updated}
