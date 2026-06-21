"""
Cost rate dictionary API (guarded by require_cost_feature; super_admin write-only)
GET /api/cost/rates   Read rates
PUT /api/cost/rates   Update rates
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
    """Read all rate configurations"""
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
    """Batch update rate configurations"""
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
    return {"message": f"Updated {len(updated)} rate items", "updated": updated}
