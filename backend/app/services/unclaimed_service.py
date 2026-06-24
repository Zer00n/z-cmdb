"""V0.6 unclaimed resources service"""
from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from app.models.consuming_unit import ConsumingUnit
from app.models.host_resource import HostResource
from app.models.placement import Placement


def get_unclaimed_resources(db: Session) -> dict:
    """
    Returns:
      - unclaimed_units: consuming_unit with project_id IS NULL
      - zombie_hosts: host_resource with monthly_cost > 0 and NO current placements
      - summary: counts and total monthly waste
    """
    # Unclaimed units (project_id is NULL)
    unclaimed = list(
        db.scalars(
            select(ConsumingUnit).where(ConsumingUnit.project_id.is_(None))
        ).all()
    )

    # Zombie hosts: no current placements at all
    hosts_with_placements = set(
        db.scalars(select(Placement.host_id).distinct()).all()
    )
    zombie_hosts = list(
        db.scalars(
            select(HostResource).where(
                and_(
                    HostResource.monthly_cost > 0,
                    ~HostResource.id.in_(hosts_with_placements) if hosts_with_placements else True,
                )
            )
        ).all()
    )

    # Calculate total monthly waste
    total_waste = sum(h.monthly_cost for h in zombie_hosts)
    # Unclaimed units' cost is estimated from their placements
    for u in unclaimed:
        placement = db.scalars(
            select(Placement).where(Placement.unit_id == u.id)
            .order_by(Placement.observed_at.desc()).limit(1)
        ).first()
        if placement:
            # Find host cost
            host = db.get(HostResource, placement.host_id)
            if host:
                # Estimate: proportional cost based on mem usage
                total_mem = sum(
                    p.mem_request * p.instances
                    for p in db.scalars(
                        select(Placement).where(Placement.unit_id == u.id)
                    ).all()
                )
                if host.mem_total > 0:
                    total_waste += host.monthly_cost * (total_mem / host.mem_total)

    return {
        "unclaimed_units": unclaimed,
        "zombie_hosts": zombie_hosts,
        "summary": {
            "unclaimed_count": len(unclaimed),
            "zombie_count": len(zombie_hosts),
            "total_monthly_waste": round(total_waste, 2),
        },
    }
