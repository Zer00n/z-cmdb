"""
Cost accounting data access layer
Department / AssetCostItem / AssetRelation / AssetDeptAssignment / CostRate
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.asset import Asset
from app.models.cost import (
    AssetCostItem,
    AssetDeptAssignment,
    AssetRelation,
    CostRate,
    Department,
)

logger = logging.getLogger(__name__)


# ── Department ─────────────────────────────────────────────────


def get_departments(db: Session) -> list[Department]:
    """List all departments"""
    return list(db.scalars(select(Department).order_by(Department.id)).all())


def get_department(db: Session, dept_id: int) -> Department:
    """Get a single department by ID"""
    dept = db.get(Department, dept_id)
    if dept is None:
        raise NotFoundError(f"Department ID {dept_id} not found")
    return dept


def create_department(db: Session, name: str, code: str) -> Department:
    """Create a department"""
    dept = Department(name=name, code=code)
    db.add(dept)
    db.flush()
    logger.info("department created", extra={"dept_id": dept.id, "dept_name": name})
    return dept


def update_department(db: Session, dept_id: int, name: str, code: str) -> Department:
    """Update a department"""
    dept = get_department(db, dept_id)
    dept.name = name
    dept.code = code
    db.flush()
    logger.info("department updated", extra={"dept_id": dept_id})
    return dept


def delete_department(db: Session, dept_id: int) -> None:
    """Delete a department"""
    dept = get_department(db, dept_id)
    db.delete(dept)
    db.flush()
    logger.info("department deleted", extra={"dept_id": dept_id})


# ── AssetCostItem ──────────────────────────────────────────────


def get_cost_items(db: Session, asset_id: int) -> list[AssetCostItem]:
    """List all cost lines for an asset"""
    stmt = (
        select(AssetCostItem)
        .where(AssetCostItem.asset_id == asset_id)
        .order_by(AssetCostItem.id)
    )
    return list(db.scalars(stmt).all())


def create_cost_item(db: Session, asset_id: int, **kwargs) -> AssetCostItem:
    """Create a cost line"""
    item = AssetCostItem(asset_id=asset_id, **kwargs)
    db.add(item)
    db.flush()
    logger.info("cost item created", extra={"item_id": item.id, "asset_id": asset_id})
    return item


def update_cost_item(db: Session, item_id: int, **kwargs) -> AssetCostItem:
    """Update a cost line"""
    item = db.get(AssetCostItem, item_id)
    if item is None:
        raise NotFoundError(f"Cost line ID {item_id} not found")
    for key, value in kwargs.items():
        if hasattr(item, key) and value is not None:
            setattr(item, key, value)
    db.flush()
    logger.info("cost item updated", extra={"item_id": item_id})
    return item


def delete_cost_item(db: Session, item_id: int) -> None:
    """Delete a cost line"""
    item = db.get(AssetCostItem, item_id)
    if item is None:
        raise NotFoundError(f"Cost line ID {item_id} not found")
    db.delete(item)
    db.flush()
    logger.info("cost item deleted", extra={"item_id": item_id})


# ── AssetRelation ──────────────────────────────────────────────


def get_relations(db: Session, asset_id: int) -> list[AssetRelation]:
    """List all relations for an asset (as source or target)"""
    stmt = (
        select(AssetRelation)
        .where(
            or_(
                AssetRelation.source_asset_id == asset_id,
                AssetRelation.target_asset_id == asset_id,
            )
        )
        .order_by(AssetRelation.id)
    )
    return list(db.scalars(stmt).all())


def create_relation(db: Session, **kwargs) -> AssetRelation:
    """Create an asset relation"""
    relation = AssetRelation(**kwargs)
    db.add(relation)
    db.flush()
    logger.info(
        "asset relation created",
        extra={
            "relation_id": relation.id,
            "source": relation.source_asset_id,
            "target": relation.target_asset_id,
        },
    )
    return relation


def delete_relation(db: Session, relation_id: int) -> None:
    """Delete an asset relation"""
    relation = db.get(AssetRelation, relation_id)
    if relation is None:
        raise NotFoundError(f"Asset relation ID {relation_id} not found")
    db.delete(relation)
    db.flush()
    logger.info("asset relation deleted", extra={"relation_id": relation_id})


# ── AssetDeptAssignment ────────────────────────────────────────


def get_dept_assignments(db: Session, asset_id: int) -> list[AssetDeptAssignment]:
    """List all department assignment records for an asset"""
    stmt = (
        select(AssetDeptAssignment)
        .where(AssetDeptAssignment.asset_id == asset_id)
        .order_by(AssetDeptAssignment.id)
    )
    return list(db.scalars(stmt).all())


def get_dept_assignments_by_dept(db: Session, dept_id: int) -> list[AssetDeptAssignment]:
    """List all asset assignment records for a department"""
    stmt = (
        select(AssetDeptAssignment)
        .where(AssetDeptAssignment.dept_id == dept_id)
        .order_by(AssetDeptAssignment.id)
    )
    return list(db.scalars(stmt).all())


def create_dept_assignment(db: Session, **kwargs) -> AssetDeptAssignment:
    """Create an asset-department assignment"""
    assignment = AssetDeptAssignment(**kwargs)
    db.add(assignment)
    db.flush()
    logger.info(
        "dept assignment created",
        extra={"assignment_id": assignment.id, "asset_id": assignment.asset_id, "dept_id": assignment.dept_id},
    )
    return assignment


def close_dept_assignment(db: Session, assignment_id: int, effective_to: str) -> AssetDeptAssignment:
    """Close an asset-department assignment (set effective_to)"""
    assignment = db.get(AssetDeptAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError(f"Department assignment ID {assignment_id} not found")
    assignment.effective_to = effective_to
    db.flush()
    logger.info("dept assignment closed", extra={"assignment_id": assignment_id, "effective_to": effective_to})
    return assignment


def delete_dept_assignment(db: Session, assignment_id: int) -> None:
    """Delete an asset-department assignment"""
    assignment = db.get(AssetDeptAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError(f"Department assignment ID {assignment_id} not found")
    db.delete(assignment)
    db.flush()
    logger.info("dept assignment deleted", extra={"assignment_id": assignment_id})


# ── CostRate ───────────────────────────────────────────────────


def get_all_cost_rates(db: Session) -> list[CostRate]:
    """List all cost rates"""
    return list(db.scalars(select(CostRate).order_by(CostRate.key)).all())


def get_cost_rate(db: Session, key: str) -> CostRate:
    """Get a single cost rate by key"""
    rate = db.get(CostRate, key)
    if rate is None:
        raise NotFoundError(f"Rate {key} not found")
    return rate


def upsert_cost_rate(
    db: Session,
    key: str,
    value,
    description: str | None = None,
    updated_by: int | None = None,
) -> CostRate:
    """Create or update a cost rate"""
    rate = db.get(CostRate, key)
    if rate is None:
        rate = CostRate(key=key)
        db.add(rate)
    if isinstance(value, str):
        rate.value = value
    else:
        rate.value = json.dumps(value, ensure_ascii=False)
    if description is not None:
        rate.description = description
    rate.updated_at = datetime.now(timezone.utc)
    rate.updated_by = updated_by
    db.flush()
    logger.info("cost rate upserted", extra={"key": key})
    return rate


def bulk_upsert_cost_rates(
    db: Session,
    rates: dict,
    updated_by: int | None = None,
) -> list[CostRate]:
    """Bulk create or update cost rates

    rates format: {key: {"value": {...}, "description": "..."}}
    """
    result = []
    for key, data in rates.items():
        rate = upsert_cost_rate(
            db,
            key=key,
            value=data["value"],
            description=data.get("description"),
            updated_by=updated_by,
        )
        result.append(rate)
    return result


# ── Asset cost queries ─────────────────────────────────────────


def get_assets_without_cost_data(db: Session) -> int:
    """Count assets without purchase price"""
    stmt = select(Asset).where(Asset.purchase_price.is_(None))
    # use the ORM count approach consistent with the rest of the codebase
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(Asset).where(Asset.purchase_price.is_(None))
    return db.scalar(count_stmt) or 0


def get_assets_by_dept(db: Session, dept_id: int) -> list[Asset]:
    """List assets assigned to the specified department"""
    stmt = (
        select(Asset)
        .where(Asset.responsible_dept_id == dept_id)
        .order_by(Asset.id)
    )
    return list(db.scalars(stmt).all())
