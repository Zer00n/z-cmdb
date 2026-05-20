"""
应用服务清单路由
GET    /api/assets/{asset_id}/apps          列出该资产所有应用
POST   /api/assets/{asset_id}/apps          新增应用
PATCH  /api/assets/{asset_id}/apps/{app_id} 修改应用
DELETE /api/assets/{asset_id}/apps/{app_id} 删除应用（软删除）
GET    /api/assets/{asset_id}/apps/export   导出该资产应用清单 CSV
GET    /api/apps/search                     全局应用搜索
GET    /api/apps/names                      应用名 autocomplete
"""
import logging

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.schemas.asset_app import (
    AssetAppCreate,
    AssetAppListResponse,
    AssetAppRead,
    AssetAppUpdate,
    AppSearchResponse,
)
from app.services import asset_app_service, audit_service

logger = logging.getLogger(__name__)

# 资产下的应用 CRUD
router = APIRouter(tags=["asset-apps"])


@router.get("/api/assets/{asset_id}/apps", response_model=AssetAppListResponse)
def list_asset_apps(
    asset_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AssetAppListResponse:
    """列出该资产所有应用"""
    return asset_app_service.list_apps(db, asset_id)


@router.post("/api/assets/{asset_id}/apps", response_model=AssetAppRead, status_code=201)
def create_asset_app(
    asset_id: int,
    body: AssetAppCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> AssetAppRead:
    """新增应用"""
    app = asset_app_service.create_app(db, asset_id, body, created_by=current_user.id)
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,
        target_type="asset_app", target_id=app.id,
        details={"asset_id": asset_id, "name": body.name, "version": body.version},
    )
    db.commit()
    return app


@router.patch("/api/assets/{asset_id}/apps/{app_id}", response_model=AssetAppRead)
def update_asset_app(
    asset_id: int,
    app_id: int,
    body: AssetAppUpdate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> AssetAppRead:
    """修改应用"""
    app = asset_app_service.update_app(db, asset_id, app_id, body)
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="asset_app", target_id=app_id,
        details=body.model_dump(exclude_none=True),
    )
    db.commit()
    return app


@router.delete("/api/assets/{asset_id}/apps/{app_id}", status_code=204)
def delete_asset_app(
    asset_id: int,
    app_id: int,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> None:
    """删除应用（软删除）"""
    asset_app_service.delete_app(db, asset_id, app_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=current_user,
        target_type="asset_app", target_id=app_id,
        details={"asset_id": asset_id, "action": "decommissioned"},
    )
    db.commit()


@router.get("/api/assets/{asset_id}/apps/export")
def export_asset_apps(
    asset_id: int,
    request: Request,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """导出该资产应用清单 CSV"""
    csv_content = asset_app_service.export_apps_csv(db, asset_id)
    audit_service.log_from_request(
        db, request, action_type="EXPORT", user=_current_user,
        target_type="asset_app", details={"asset_id": asset_id, "format": "csv"},
    )
    db.commit()
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=asset_{asset_id}_apps.csv"},
    )


# 全局应用搜索 & autocomplete
@router.get("/api/apps/search", response_model=AppSearchResponse)
def search_apps(
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AppSearchResponse:
    """全局应用搜索（按 name 或 version 模糊匹配）"""
    return asset_app_service.search_apps(db, q)


@router.get("/api/apps/names")
def get_app_names(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[str]:
    """返回所有已存在的应用名（去重，用于前端 autocomplete）"""
    return asset_app_service.get_app_names(db)
