"""V0.6 placement repository"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.consuming_unit import ConsumingUnit
from app.models.placement import Placement


def create_placement(db: Session, **kwargs) -> Placement:
    placement = Placement(**kwargs)
    db.add(placement)
    db.commit()
    db.refresh(placement)
    return placement


def get_current_placement(db: Session, unit_id: str) -> Placement | None:
    """Get the most recent placement for a unit."""
    return db.scalars(
        select(Placement)
        .where(Placement.unit_id == unit_id)
        .order_by(Placement.observed_at.desc())
        .limit(1)
    ).first()


def get_placements_on_host(db: Session, host_id: str) -> list[Placement]:
    """Get all current placements on a host (latest per unit)."""
    # Get the latest placement per unit on this host
    subq = (
        select(
            Placement.unit_id,
            func.max(Placement.observed_at).label("max_observed"),
        )
        .where(Placement.host_id == host_id)
        .group_by(Placement.unit_id)
        .subquery()
    )
    return list(
        db.scalars(
            select(Placement).join(
                subq,
                (Placement.unit_id == subq.c.unit_id)
                & (Placement.observed_at == subq.c.max_observed),
            )
        ).all()
    )


def get_placements_for_project(db: Session, project_id: str) -> list[Placement]:
    """Get current placements for all units in a project."""
    subq = (
        select(
            Placement.unit_id,
            func.max(Placement.observed_at).label("max_observed"),
        )
        .join(ConsumingUnit, ConsumingUnit.id == Placement.unit_id)
        .where(ConsumingUnit.project_id == project_id)
        .group_by(Placement.unit_id)
        .subquery()
    )
    return list(
        db.scalars(
            select(Placement).join(
                subq,
                (Placement.unit_id == subq.c.unit_id)
                & (Placement.observed_at == subq.c.max_observed),
            )
        ).all()
    )


def has_any_placement(db: Session, host_id: str) -> bool:
    """Check if a host has any placements at all."""
    return db.scalar(
        select(func.count()).select_from(Placement).where(Placement.host_id == host_id)
    ) > 0
