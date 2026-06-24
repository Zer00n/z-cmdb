"""V0.6 consuming unit repository"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import UnitNotFoundError
from app.models.consuming_unit import ConsumingUnit


def get_by_id(db: Session, unit_id: str) -> ConsumingUnit:
    unit = db.get(ConsumingUnit, unit_id)
    if not unit:
        raise UnitNotFoundError(f"Consuming unit {unit_id} not found")
    return unit


def list_unclaimed(db: Session) -> list[ConsumingUnit]:
    return list(
        db.scalars(
            select(ConsumingUnit).where(ConsumingUnit.project_id.is_(None))
        ).all()
    )


def list_by_project(db: Session, project_id: str) -> list[ConsumingUnit]:
    return list(
        db.scalars(
            select(ConsumingUnit)
            .where(ConsumingUnit.project_id == project_id)
            .order_by(ConsumingUnit.id)
        ).all()
    )


def update_unit(db: Session, unit: ConsumingUnit, **kwargs) -> ConsumingUnit:
    for key, value in kwargs.items():
        setattr(unit, key, value)
    db.commit()
    db.refresh(unit)
    return unit


def claim_unit(db: Session, unit: ConsumingUnit, project_id: str) -> ConsumingUnit:
    unit.project_id = project_id
    db.commit()
    db.refresh(unit)
    return unit
