"""
Import Preset business logic
"""
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, NotFoundError
from app.models.asset import Asset
from app.models.import_preset import ImportPreset
from app.repositories import import_preset_repo


def create_preset(
    db: Session,
    category: str,
    value: str,
    is_default: bool = False,
    sort_order: int = 0,
    remark: str | None = None,
    user_id: int | None = None,
) -> ImportPreset:
    if import_preset_repo.exists(db, category, value):
        raise DuplicateError(f"Preset value '{value}' already exists in category '{category}'")

    obj = import_preset_repo.create(
        db,
        category=category,
        value=value,
        is_default=0,
        sort_order=sort_order,
        remark=remark,
        created_by=user_id,
    )
    db.flush()

    if is_default:
        set_default(db, obj.id)
        db.refresh(obj)

    return obj


def update_preset(
    db: Session,
    preset_id: int,
    value: str | None = None,
    sort_order: int | None = None,
    remark: str | None = None,
) -> ImportPreset:
    obj = import_preset_repo.get_by_id(db, preset_id)
    if obj is None:
        raise NotFoundError(f"Preset ID {preset_id} not found")

    if value is not None:
        if value != obj.value and import_preset_repo.exists(db, obj.category, value):
            raise DuplicateError(f"Preset value '{value}' already exists in category '{obj.category}'")
        obj.value = value
    if sort_order is not None:
        obj.sort_order = sort_order
    if remark is not None:
        obj.remark = remark

    db.flush()
    return obj


def set_default(db: Session, preset_id: int) -> ImportPreset:
    """Set a preset as default. Clears existing default in the same transaction."""
    obj = import_preset_repo.get_by_id(db, preset_id)
    if obj is None:
        raise NotFoundError(f"Preset ID {preset_id} not found")

    # Clear existing default for this category first
    import_preset_repo.clear_default(db, obj.category)
    db.flush()

    # Set new default
    obj.is_default = 1
    db.flush()
    return obj


def delete_preset(db: Session, preset_id: int) -> None:
    obj = import_preset_repo.get_by_id(db, preset_id)
    if obj is None:
        raise NotFoundError(f"Preset ID {preset_id} not found")
    db.delete(obj)
    db.flush()


def sync_from_assets(db: Session) -> dict[str, int]:
    """Extract distinct values from existing assets and add to presets."""
    result = {}
    field_map = {
        "location": Asset.location,
        "owner": Asset.owner,
        "business_system": Asset.business_system,
    }
    for category, column in field_map.items():
        added = 0
        for v in import_preset_repo.distinct_asset_values(db, column):
            if not import_preset_repo.exists(db, category, v):
                import_preset_repo.create(db, category=category, value=v)
                added += 1
        result[category] = added
    db.flush()
    return result
