"""
Import Preset API router
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.schemas.import_preset import (
    PresetCategory,
    PresetCreate,
    PresetOut,
    PresetUpdate,
    SyncResult,
)
from app.services import audit_service, import_preset_service

router = APIRouter(prefix="/api/import-presets", tags=["import-presets"])


@router.get("", response_model=list[PresetOut])
def list_presets(
    category: PresetCategory | None = None,
    q: str | None = None,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
):
    from app.repositories import import_preset_repo

    return import_preset_repo.list_presets(db, category=category, q=q)


@router.get("/categories")
def categories():
    return [
        {"key": c.value, "label_key": f"preset.category.{c.value}"}
        for c in PresetCategory
    ]


@router.post("", response_model=PresetOut)
def create_preset(
    data: PresetCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    obj = import_preset_service.create_preset(
        db,
        category=data.category.value,
        value=data.value,
        is_default=data.is_default,
        sort_order=data.sort_order,
        remark=data.remark,
        user_id=current_user.id,
    )
    audit_service.log_from_request(
        db, request,
        action_type="CREATE",
        user=current_user,
        target_type="import_preset",
        target_id=obj.id,
        details={"category": obj.category, "value": obj.value},
    )
    db.commit()
    return obj


@router.put("/{preset_id}", response_model=PresetOut)
def update_preset(
    preset_id: int,
    data: PresetUpdate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    obj = import_preset_service.update_preset(
        db,
        preset_id=preset_id,
        value=data.value,
        sort_order=data.sort_order,
        remark=data.remark,
    )
    audit_service.log_from_request(
        db, request,
        action_type="UPDATE",
        user=current_user,
        target_type="import_preset",
        target_id=obj.id,
        details={"category": obj.category, "value": obj.value},
    )
    db.commit()
    return obj


@router.patch("/{preset_id}/default", response_model=PresetOut)
def set_default(
    preset_id: int,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    obj = import_preset_service.set_default(db, preset_id)
    audit_service.log_from_request(
        db, request,
        action_type="UPDATE",
        user=current_user,
        target_type="import_preset",
        target_id=obj.id,
        details={"category": obj.category, "value": obj.value, "action": "set_default"},
    )
    db.commit()
    return obj


@router.delete("/{preset_id}")
def delete_preset(
    preset_id: int,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    from app.repositories import import_preset_repo

    obj = import_preset_repo.get_by_id(db, preset_id)
    details = {"category": obj.category, "value": obj.value} if obj else {}

    import_preset_service.delete_preset(db, preset_id)
    audit_service.log_from_request(
        db, request,
        action_type="DELETE",
        user=current_user,
        target_type="import_preset",
        target_id=preset_id,
        details=details,
    )
    db.commit()
    return {"message": "Preset deleted"}


@router.post("/sync-from-assets", response_model=SyncResult)
def sync_from_assets(
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    result = import_preset_service.sync_from_assets(db)
    audit_service.log_from_request(
        db, request,
        action_type="CREATE",
        user=current_user,
        target_type="import_preset",
        target_id=None,
        details={"action": "sync_from_assets", **result},
    )
    db.commit()
    return result
