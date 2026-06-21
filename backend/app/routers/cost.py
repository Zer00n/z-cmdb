"""
Asset cost API (guarded by require_cost_feature)
GET    /api/assets/{id}/cost               Single asset full-loaded cost breakdown
GET    /api/cost/summary                    Cost dashboard aggregate
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, RequireCostFeature
from app.models.asset import Asset
from app.repositories import cost_repo
from app.core.exceptions import AssetNotFoundError
from app.services import cost_service

router = APIRouter(tags=["cost"])


@router.get("/api/assets/{asset_id}/cost")
def get_asset_cost(
    asset_id: int,
    _feature: RequireCostFeature = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Single asset full-loaded cost breakdown, net value, and remaining depreciation months"""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise AssetNotFoundError()

    result = cost_service.compute_asset_full_cost(db, asset)
    return result


@router.get("/api/cost/summary")
def get_cost_summary(
    _feature: RequireCostFeature = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Cost dashboard aggregate: KPI + chart data + governance checklist"""
    summary = cost_service.compute_global_summary(db)
    return summary
