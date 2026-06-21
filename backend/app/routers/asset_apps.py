"""
Application service catalog routes
GET    /api/assets/{asset_id}/apps          List all apps on this asset
POST   /api/assets/{asset_id}/apps          Add app
PATCH  /api/assets/{asset_id}/apps/{app_id} Update app
DELETE /api/assets/{asset_id}/apps/{app_id} Delete app (soft delete)
GET    /api/assets/{asset_id}/apps/export   Export this asset's app catalog as CSV
GET    /api/apps/search                     Global app search
GET    /api/apps/names                      App name autocomplete
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

# CRUD for apps under an asset
router = APIRouter(tags=["asset-apps"])


@router.get("/api/assets/{asset_id}/apps", response_model=AssetAppListResponse)
def list_asset_apps(
    asset_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AssetAppListResponse:
    """List all apps on this asset"""
    return asset_app_service.list_apps(db, asset_id)


@router.post("/api/assets/{asset_id}/apps", response_model=AssetAppRead, status_code=201)
def create_asset_app(
    asset_id: int,
    body: AssetAppCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> AssetAppRead:
    """Add app"""
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
    """Update app"""
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
    """Delete app (soft delete)"""
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
    """Export this asset's app catalog as CSV"""
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


# Global app search & autocomplete
@router.get("/api/apps/search", response_model=AppSearchResponse)
def search_apps(
    q: str = Query(..., min_length=1, max_length=100, description="Search keyword"),
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AppSearchResponse:
    """Global app search (fuzzy match by name or version)"""
    return asset_app_service.search_apps(db, q)


@router.get("/api/apps/names")
def get_app_names(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[str]:
    """Return all existing app names (deduplicated, for frontend autocomplete)"""
    return asset_app_service.get_app_names(db)
