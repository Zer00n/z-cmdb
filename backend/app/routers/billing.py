"""
部门账单接口（受 require_cost_feature 守卫）
GET /api/billing/department/{dept_id}?from=&to=&granularity=
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, RequireCostFeature
from app.services import billing_service

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/department/{dept_id}")
def get_department_bill(
    dept_id: int,
    date_from: str = Query(..., alias="from", description="账单起始日 YYYY-MM-DD"),
    date_to: str = Query(..., alias="to", description="账单截止日 YYYY-MM-DD"),
    granularity: str = Query("month", description="粒度: day/month/year"),
    _feature: RequireCostFeature = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """部门账单"""
    return billing_service.department_bill(db, dept_id, date_from, date_to, granularity)
