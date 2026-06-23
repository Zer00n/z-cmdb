"""
Asset management routes
GET    /api/assets          Asset list (filter/search/paginate)
POST   /api/assets          Manually add an asset
GET    /api/assets/export   CSV export
GET    /api/assets/{id}     Asset detail
PATCH  /api/assets/{id}     Update asset
DELETE /api/assets/{id}     Decommission asset (soft delete)
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
    """Asset list with filtering, search, and pagination"""
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
    """Export asset list as CSV"""
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


@router.get("/export-threat-hunting")
def export_assets_threat_hunting(
    search: str | None = None,
    asset_type: str | None = None,
    network_zone: str | None = None,
    importance: str | None = None,
    status: str | None = None,
    business_system: str | None = None,
    owner: str | None = None,
    source: str | None = None,
    skip_empty_apps: bool = False,
    include_decommissioned: bool = False,
    default_environment: str = "prod",
    request: Request = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """Export assets and apps as a threat-hunting-compatible CSV"""
    from datetime import date

    params = AssetQueryParams(
        page=1,
        page_size=10000,
        search=search,
        asset_type=asset_type,  # type: ignore[arg-type]
        network_zone=network_zone,  # type: ignore[arg-type]
        importance=importance,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        business_system=business_system,
        owner=owner,
        source=source,  # type: ignore[arg-type]
    )
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(
        db, params,
        skip_empty_apps=skip_empty_apps,
        include_decommissioned=include_decommissioned,
        default_environment=default_environment,
    )
    audit_service.log_from_request(
        db, request, action_type="EXPORT", user=_current_user,  # type: ignore[arg-type]
        target_type="asset",
        details={"format": "csv", "template": "threat_hunting", "row_count": row_count},
    )
    db.commit()
    filename = f"cmdb_threat_hunting_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_content.encode("utf-8-sig"),  # BOM for Excel
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> AssetRead:
    """Asset detail (including port list)"""
    return asset_service.get_asset(db, asset_id)  # type: ignore[return-value]


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(
    body: AssetCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> AssetRead:
    """Manually add an asset (requires admin permission)"""
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
    """Update asset information (requires admin permission)"""
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
    """Decommission asset (soft delete, marks as decommissioned; requires admin permission)"""
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
    """Asset port change history (based on scan snapshots)"""
    return asset_service.get_asset_history(db, asset_id)


@router.patch("/bulk")
def bulk_update_assets(
    body: dict,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Bulk update assets.
    body: { "ids": [1,2,3], "updates": {"owner": "John"} }
    Supported fields: owner, status, business_system, importance, network_zone
    """
    ids = body.get("ids", [])
    updates = body.get("updates", {})
    if not ids or not updates:
        from app.core.exceptions import ValidationError
        raise ValidationError("ids and updates cannot be empty")

    allowed_fields = {"owner", "status", "business_system", "importance", "network_zone", "location"}
    filtered = {k: v for k, v in updates.items() if k in allowed_fields}
    if not filtered:
        from app.core.exceptions import ValidationError
        raise ValidationError(f"Bulk-modifiable fields not supported, allowed: {allowed_fields}")

    # 枚举字段值校验（与 schemas/asset.py 中的 Literal 定义保持一致）
    _enum_whitelist = {
        "status": {"online", "offline", "decommissioned"},
        "importance": {"core", "important", "normal"},
        "network_zone": {
            "dmz", "intranet", "office", "management", "other",
            "aliyun", "tencent", "huawei", "aws", "azure", "gcp", "other_cloud",
        },
    }
    from app.core.exceptions import ValidationError
    for _field, _allowed in _enum_whitelist.items():
        if _field in filtered and filtered[_field] not in _allowed:
            raise ValidationError(
                f"Invalid value for '{_field}': {filtered[_field]!r}. Allowed: {sorted(_allowed)}"
            )

    count = asset_service.bulk_update(db, ids, filtered)
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="asset",
        details={"action": "bulk_update", "count": count, "updates": filtered, "ids": ids},
    )
    db.commit()
    return {"message": f"Successfully bulk-updated {count} assets", "count": count}
