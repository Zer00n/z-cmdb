"""V0.6 unit relation repository"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.unit_relation import UnitRelation


def get_by_id(db: Session, relation_id: str) -> UnitRelation | None:
    return db.get(UnitRelation, relation_id)


def list_by_units(db: Session, unit_ids: set[str]) -> list[UnitRelation]:
    if not unit_ids:
        return []
    return list(
        db.scalars(
            select(UnitRelation).where(
                (UnitRelation.source_unit_id.in_(unit_ids))
                | (UnitRelation.target_unit_id.in_(unit_ids))
            ).order_by(UnitRelation.id)
        ).all()
    )


def create_relation(db: Session, **kwargs) -> UnitRelation:
    rel = UnitRelation(**kwargs)
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def delete_relation(db: Session, rel: UnitRelation) -> None:
    db.delete(rel)
    db.commit()
