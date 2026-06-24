"""V0.6 bill generation service (on-read freeze pattern)"""
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.engine.apportion import (
    HostInput,
    PlacementInput,
    PolicyInput,
    UnitInput,
    apportion,
)
from app.models.consuming_unit import ConsumingUnit
from app.models.host_resource import HostResource
from app.models.placement import Placement
from app.repositories import billing_repo, placement_repo


def get_or_generate_bill(db: Session, project_id: str, period: str) -> dict:
    """
    Get an existing bill snapshot, or generate one on-read.

    Once generated, the snapshot is frozen and never recalculated.
    """
    # Check for existing snapshot
    snapshot = billing_repo.get_bill_snapshot(db, project_id, period)
    if snapshot:
        return {
            "id": snapshot.id,
            "project_id": snapshot.project_id,
            "period": snapshot.period,
            "policy_version": snapshot.policy_version,
            "total_cost": snapshot.total_cost,
            "detail": json.loads(snapshot.detail_json),
            "generated_at": snapshot.generated_at.isoformat(),
            "frozen": True,
        }

    # No snapshot exists — generate one
    return _generate_bill(db, project_id, period)


def _generate_bill(db: Session, project_id: str, period: str) -> dict:
    """Run the apportion engine and create a frozen snapshot."""
    # Get active policy
    policy_row = billing_repo.get_active_policy(db)
    if not policy_row:
        return {"error": "No active billing policy"}

    policy = PolicyInput(
        denominator=policy_row.denominator,
        weight_mode=policy_row.weight_mode,
        weight_cpu=policy_row.weight_cpu,
        weight_mem=policy_row.weight_mem,
        idle_cost=policy_row.idle_cost,
    )

    # Get all hosts
    hosts = list(db.scalars(select(HostResource)).all())
    # get all placements
    all_placements = list(db.scalars(select(Placement)).all())
    # get all units
    all_units = list(db.scalars(select(ConsumingUnit)).all())

    # Run apportion
    result = apportion(
        hosts=[HostInput(id=h.id, cpu_total=h.cpu_total, mem_total=h.mem_total, monthly_cost=h.monthly_cost) for h in hosts],
        placements=[PlacementInput(id=p.id, unit_id=p.unit_id, host_id=p.host_id, cpu_request=p.cpu_request, mem_request=p.mem_request, instances=p.instances) for p in all_placements],
        units=[UnitInput(id=u.id, project_id=u.project_id) for u in all_units],
        policy=policy,
    )

    # Get this project's cost
    project_cost = result.project_cost.get(project_id, 0.0)

    # Build detail
    detail = {
        "project_cost": project_cost,
        "bucket_idle": result.bucket_idle,
        "lines": [
            {"unit_id": d.unit_id, "host_id": d.host_id, "share": d.share, "amount": d.amount}
            for d in result.detail
            if _unit_belongs_to_project(db, d.unit_id, project_id)
        ],
    }

    # Create snapshot
    snapshot = billing_repo.create_bill_snapshot(
        db,
        project_id=project_id,
        period=period,
        policy_version=policy_row.version,
        total_cost=project_cost,
        detail_json=json.dumps(detail),
    )

    return {
        "id": snapshot.id,
        "project_id": project_id,
        "period": period,
        "policy_version": policy_row.version,
        "total_cost": project_cost,
        "detail": detail,
        "generated_at": snapshot.generated_at.isoformat(),
        "frozen": True,
    }


def _unit_belongs_to_project(db: Session, unit_id: str, project_id: str) -> bool:
    unit = db.get(ConsumingUnit, unit_id)
    return unit is not None and unit.project_id == project_id


# Need to import select for the _generate_bill function
from sqlalchemy import select
