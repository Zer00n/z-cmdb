"""
资产关系接口（受 require_cost_feature 守卫）
GET    /api/assets/{id}/relations          资产关系列表
POST   /api/assets/{id}/relations          创建关系
DELETE /api/assets/{id}/relations/{rid}    删除关系
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser, RequireCostFeature
from app.repositories import cost_repo
from app.services import audit_service

router = APIRouter(tags=["asset-relations"])


class RelationCreate(BaseModel):
    target_asset_id: int
    relation_type: str
    driver_type: str = "even"
    driver_value: float | None = None
    effective_from: str | None = None
    effective_to: str | None = None


@router.get("/api/assets/{asset_id}/relations")
def list_relations(
    asset_id: int,
    _feature: RequireCostFeature = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """资产关系列表（source 或 target 为该资产）"""
    relations = cost_repo.get_relations(db, asset_id)
    return [
        {
            "id": r.id,
            "source_asset_id": r.source_asset_id,
            "target_asset_id": r.target_asset_id,
            "relation_type": r.relation_type,
            "driver_type": r.driver_type,
            "driver_value": r.driver_value,
            "effective_from": r.effective_from,
            "effective_to": r.effective_to,
        }
        for r in relations
    ]


@router.post("/api/assets/{asset_id}/relations")
def create_relation(
    asset_id: int,
    body: RelationCreate,
    request: Request,
    _feature: RequireCostFeature = None,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """创建资产关系"""
    rel = cost_repo.create_relation(
        db,
        source_asset_id=asset_id,
        target_asset_id=body.target_asset_id,
        relation_type=body.relation_type,
        driver_type=body.driver_type,
        driver_value=body.driver_value,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
    )
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,
        target_type="asset_relation", target_id=str(rel.id),
    )
    db.commit()
    return {
        "id": rel.id,
        "source_asset_id": rel.source_asset_id,
        "target_asset_id": rel.target_asset_id,
        "relation_type": rel.relation_type,
        "driver_type": rel.driver_type,
        "driver_value": rel.driver_value,
    }


@router.delete("/api/assets/{asset_id}/relations/{relation_id}")
def delete_relation(
    asset_id: int,
    relation_id: int,
    request: Request,
    _feature: RequireCostFeature = None,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """删除资产关系"""
    cost_repo.delete_relation(db, relation_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=current_user,
        target_type="asset_relation", target_id=str(relation_id),
    )
    db.commit()
    return {"message": "关系已删除"}
