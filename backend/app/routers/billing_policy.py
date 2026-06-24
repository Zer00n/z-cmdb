"""V0.6 billing policy router — /api/billing-policy"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, AdminUser
from app.schemas.billing_policy import BillingPolicyRead, BillingPolicyUpdate
from app.services import billing_policy_service

router = APIRouter(prefix="/api/billing-policy", tags=["billing-policy"])


@router.get("", response_model=BillingPolicyRead)
def get_policy(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
):
    """Get the current active billing policy."""
    policy = billing_policy_service.get_active_policy(db)
    if not policy:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "No active policy"})
    return policy


@router.put("", response_model=BillingPolicyRead)
def update_policy(
    db: Annotated[Session, Depends(get_db)],
    _user: AdminUser,
    data: BillingPolicyUpdate,
):
    """
    Update billing policy by creating a new version.
    The old version is preserved. freeze is always true.
    """
    return billing_policy_service.update_policy(
        db,
        denominator=data.denominator,
        weight_mode=data.weight_mode,
        weight_cpu=data.weight_cpu,
        weight_mem=data.weight_mem,
        idle_cost=data.idle_cost,
        sampling=data.sampling,
    )
