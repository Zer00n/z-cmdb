"""
Asset cost line items and department assignment API
GET/POST    /api/assets/{id}/cost-items
DELETE      /api/assets/{id}/cost-items/{item_id}
GET/POST    /api/assets/{id}/dept-assignments
DELETE      /api/assets/{id}/dept-assignments/{assignment_id}
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser, RequireCostFeature
from app.repositories import cost_repo
from app.services import audit_service

router = APIRouter(tags=["asset-cost-details"])


# ── Cost Items ───────────────────────────────────────────

class CostItemCreate(BaseModel):
    cost_type: str
    amount: float
    currency: str = "CNY"
    billing_cycle: str = "month"
    effective_from: str | None = None
    effective_to: str | None = None
    tax_included: bool = True
    note: str | None = None


@router.get("/api/assets/{asset_id}/cost-items")
def list_cost_items(
    asset_id: int,
    _feature: RequireCostFeature = None,
    _user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    items = cost_repo.get_cost_items(db, asset_id)
    return [
        {
            "id": i.id, "asset_id": i.asset_id, "cost_type": i.cost_type,
            "amount": i.amount, "currency": i.currency, "billing_cycle": i.billing_cycle,
            "effective_from": i.effective_from, "effective_to": i.effective_to,
            "tax_included": i.tax_included, "note": i.note,
        }
        for i in items
    ]


@router.post("/api/assets/{asset_id}/cost-items")
def create_cost_item(
    asset_id: int,
    body: CostItemCreate,
    request: Request,
    _feature: RequireCostFeature = None,
    user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    item = cost_repo.create_cost_item(db, asset_id=asset_id, **body.model_dump())
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=user,
        target_type="cost_item", target_id=str(item.id),
    )
    db.commit()
    return {
        "id": item.id, "asset_id": item.asset_id, "cost_type": item.cost_type,
        "amount": item.amount, "currency": item.currency, "billing_cycle": item.billing_cycle,
    }


@router.delete("/api/assets/{asset_id}/cost-items/{item_id}")
def delete_cost_item(
    asset_id: int,
    item_id: int,
    request: Request,
    _feature: RequireCostFeature = None,
    user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    cost_repo.delete_cost_item(db, item_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=user,
        target_type="cost_item", target_id=str(item_id),
    )
    db.commit()
    return {"message": "Cost item deleted"}


# ── Dept Assignments ─────────────────────────────────────

class DeptAssignmentCreate(BaseModel):
    dept_id: int
    billing_mode: str = "cost"
    share_or_usage: str | None = None
    effective_from: str = "2024-01-01"


@router.get("/api/assets/{asset_id}/dept-assignments")
def list_dept_assignments(
    asset_id: int,
    _feature: RequireCostFeature = None,
    _user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    assigns = cost_repo.get_dept_assignments(db, asset_id)
    return [
        {
            "id": a.id, "asset_id": a.asset_id, "dept_id": a.dept_id,
            "billing_mode": a.billing_mode, "share_or_usage": a.share_or_usage,
            "effective_from": a.effective_from, "effective_to": a.effective_to,
        }
        for a in assigns
    ]


@router.post("/api/assets/{asset_id}/dept-assignments")
def create_dept_assignment(
    asset_id: int,
    body: DeptAssignmentCreate,
    request: Request,
    _feature: RequireCostFeature = None,
    user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    assign = cost_repo.create_dept_assignment(db, asset_id=asset_id, **body.model_dump())
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=user,
        target_type="dept_assignment", target_id=str(assign.id),
    )
    db.commit()
    return {
        "id": assign.id, "asset_id": assign.asset_id, "dept_id": assign.dept_id,
        "billing_mode": assign.billing_mode, "effective_from": assign.effective_from,
    }


@router.delete("/api/assets/{asset_id}/dept-assignments/{assignment_id}")
def delete_dept_assignment(
    asset_id: int,
    assignment_id: int,
    request: Request,
    _feature: RequireCostFeature = None,
    user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    cost_repo.delete_dept_assignment(db, assignment_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=user,
        target_type="dept_assignment", target_id=str(assignment_id),
    )
    db.commit()
    return {"message": "Assignment deleted"}
