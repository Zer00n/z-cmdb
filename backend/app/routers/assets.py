"""
资产管理路由
GET    /api/assets          资产列表（筛选/搜索/分页）
POST   /api/assets          手动新增资产
GET    /api/assets/export   CSV 导出
GET    /api/assets/{id}     资产详情
PATCH  /api/assets/{id}     更新资产
DELETE /api/assets/{id}     下线资产（软删除）
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.schemas.asset import (
    AssetCreate, AssetListResponse, AssetQueryParams, AssetRead, AssetUpdate,
)
from app.services import asset_service, audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
def list_assets(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 20,
    search: str | None = None,
    asset_type: str | None = None,
    network_zone: str | None = None,
    importance: str | None = None,
    status: str | None = None,
    business_system: str | None = None,
    owner: str | None = None,
    source: str | None = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AssetListResponse:
    """资产列表，支持筛选、搜索、分页"""
    params = AssetQueryParams(
        page=page,
        page_size=page_size,
        search=search,
        asset_type=asset_type,  # type: ignore[arg-type]
        network_zone=network_zone,  # type: ignore[arg-type]
        importance=importance,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        business_system=business_system,
        owner=owner,
        source=source,  # type: ignore[arg-type]
    )
    return asset_service.list_assets(db, params)


@router.get("/export")
def export_assets(
    search: str | None = None,
    asset_type: str | None = None,
    network_zone: str | None = None,
    importance: str | None = None,
    status: str | None = None,
    request: Request = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """导出资产列表为 CSV"""
    params = AssetQueryParams(
        page=1,
        page_size=10000,
        search=search,
        asset_type=asset_type,  # type: ignore[arg-type]
        network_zone=network_zone,  # type: ignore[arg-type]
        importance=importance,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
    )
    csv_content = asset_service.export_assets_csv(db, params)
    audit_service.log_from_request(
        db, request, action_type="EXPORT", user=_current_user,  # type: ignore[arg-type]
        target_type="asset", details={"format": "csv"},
    )
    db.commit()
    return Response(
        content=csv_content.encode("utf-8-sig"),  # BOM for Excel
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assets.csv"},
    )


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AssetRead:
    """资产详情（含端口列表）"""
    return asset_service.get_asset(db, asset_id)  # type: ignore[return-value]


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(
    body: AssetCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> AssetRead:
    """手动新增资产（需要 admin 权限）"""
    asset = asset_service.create_asset(db, body)
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,
        target_type="asset", target_id=asset.id,
        details={"asset_no": asset.asset_no, "ip": asset.ip_address},
    )
    db.commit()
    return asset  # type: ignore[return-value]


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: int,
    body: AssetUpdate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> AssetRead:
    """更新资产信息（需要 admin 权限）"""
    asset = asset_service.update_asset(db, asset_id, body)
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="asset", target_id=asset_id,
        details=body.model_dump(exclude_none=True),
    )
    db.commit()
    return asset  # type: ignore[return-value]


@router.delete("/{asset_id}", status_code=204)
def decommission_asset(
    asset_id: int,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> None:
    """下线资产（软删除，标记为 decommissioned，需要 admin 权限）"""
    asset_service.decommission_asset(db, asset_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=current_user,
        target_type="asset", target_id=asset_id,
        details={"action": "decommissioned"},
    )
    db.commit()


@router.get("/{asset_id}/history")
def get_asset_history(
    asset_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """资产端口变化历史（基于扫描快照）"""
    return asset_service.get_asset_history(db, asset_id)


@router.patch("/bulk")
def bulk_update_assets(
    body: dict,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    批量更新资产。
    body: { "ids": [1,2,3], "updates": {"owner": "张三"} }
    支持字段：owner, status, business_system, importance, network_zone
    """
    ids = body.get("ids", [])
    updates = body.get("updates", {})
    if not ids or not updates:
        from app.core.exceptions import ValidationError
        raise ValidationError("ids 和 updates 不能为空")

    allowed_fields = {"owner", "status", "business_system", "importance", "network_zone"}
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    if not filtered:
        from app.core.exceptions import ValidationError
        raise ValidationError(f"不支持批量修改的字段，允许: {allowed_fields}")

    count = asset_service.bulk_update(db, ids, filtered)
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="asset",
        details={"action": "bulk_update", "count": count, "updates": filtered, "ids": ids},
    )
    db.commit()
    return {"message": f"已批量更新 {count} 个资产", "count": count}
