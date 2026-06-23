"""
Import Preset data access layer
"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.import_preset import ImportPreset


def list_presets(
    db: Session,
    category: str | None = None,
    q: str | None = None,
) -> list[ImportPreset]:
    stmt = select(ImportPreset)
    if category:
        stmt = stmt.where(ImportPreset.category == category)
    if q:
        stmt = stmt.where(ImportPreset.value.like(f"%{q}%"))
    stmt = stmt.order_by(ImportPreset.sort_order.asc(), ImportPreset.value.asc())
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, preset_id: int) -> ImportPreset | None:
    return db.get(ImportPreset, preset_id)


def exists(db: Session, category: str, value: str) -> bool:
    return (
        db.scalar(
            select(ImportPreset.id).where(
                ImportPreset.category == category,
                ImportPreset.value == value,
            )
        )
        is not None
    )


def create(
    db: Session,
    category: str,
    value: str,
    is_default: int = 0,
    sort_order: int = 0,
    remark: str | None = None,
    created_by: int | None = None,
) -> ImportPreset:
    obj = ImportPreset(
        category=category,
        value=value,
        is_default=is_default,
        sort_order=sort_order,
        remark=remark,
        created_by=created_by,
    )
    db.add(obj)
    db.flush()
    return obj


def clear_default(db: Session, category: str) -> None:
    """Clear existing default for a category. Must be followed by flush()."""
    for p in db.scalars(
        select(ImportPreset).where(
            ImportPreset.category == category,
            ImportPreset.is_default == 1,
        )
    ).all():
        p.is_default = 0


def distinct_asset_values(db: Session, column) -> list[str]:
    """Get distinct non-empty values from an asset column."""
    from app.models.asset import Asset

    stmt = (
        select(column)
        .where(column.is_not(None), func.trim(column) != "")
        .distinct()
    )
    return [v for v in db.scalars(stmt).all() if v and v.strip()]
