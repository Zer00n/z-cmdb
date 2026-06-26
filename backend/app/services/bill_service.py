"""V0.6 bill generation service (on-read freeze pattern)"""
import json
from datetime import datetime, timezone

from sqlalchemy import select
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
    Returns enriched data with names, host details, and previous period comparison.
    """
    # Check for existing snapshot
    snapshot = billing_repo.get_bill_snapshot(db, project_id, period)
    if snapshot:
        detail = json.loads(snapshot.detail_json)
        enriched = _enrich_bill(db, project_id, detail, snapshot.policy_version)
        return {
            "id": snapshot.id,
            "project_id": snapshot.project_id,
            "period": snapshot.period,
            "policy_version": snapshot.policy_version,
            "total_cost": snapshot.total_cost,
            "detail": enriched,
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

    enriched = _enrich_bill(db, project_id, detail, policy_row.version)

    return {
        "id": snapshot.id,
        "project_id": project_id,
        "period": period,
        "policy_version": policy_row.version,
        "total_cost": project_cost,
        "detail": enriched,
        "generated_at": snapshot.generated_at.isoformat(),
        "frozen": True,
    }


def _enrich_bill(db: Session, project_id: str, detail: dict, policy_version: int) -> dict:
    """
    Enrich bill detail with names, host info, previous period comparison,
    and host_details for shared-host explanation.
    """
    # Preload lookup maps
    all_hosts = {h.id: h for h in db.scalars(select(HostResource)).all()}
    all_units = {u.id: u for u in db.scalars(select(ConsumingUnit)).all()}

    # Enrich each line with names and host info
    enriched_lines = []
    for line in detail.get("lines", []):
        unit = all_units.get(line["unit_id"])
        host = all_hosts.get(line["host_id"])

        # Find placement for this unit on this host
        placement = db.scalars(
            select(Placement).where(
                Placement.unit_id == line["unit_id"],
                Placement.host_id == line["host_id"],
            ).order_by(Placement.observed_at.desc())
        ).first()

        mem_request_total = 0.0
        if placement:
            mem_request_total = placement.mem_request * placement.instances

        enriched_lines.append({
            **line,
            "unit_name": unit.name if unit else line["unit_id"],
            "host_name": host.name if host else line["host_id"],
            "host_ip": host.ip_address if host else None,
            "host_monthly_cost": host.monthly_cost if host else 0.0,
            "mem_request_total": mem_request_total,
            "mem_total": host.mem_total if host else 0.0,
        })

    # Host details: for each host referenced in lines, compute allocation summary
    host_ids_in_lines = {line["host_id"] for line in detail.get("lines", [])}
    host_details = []
    for hid in host_ids_in_lines:
        host = all_hosts.get(hid)
        if not host:
            continue
        # Sum allocations on this host from project's lines
        allocated_on_host = sum(
            line["amount"] for line in detail.get("lines", [])
            if line["host_id"] == hid
        )
        allocated_share = sum(
            line["share"] for line in detail.get("lines", [])
            if line["host_id"] == hid
        )
        host_details.append({
            "host_id": hid,
            "name": host.name,
            "ip": host.ip_address,
            "monthly_cost": host.monthly_cost,
            "mem_total": host.mem_total,
            "allocated_cost": round(allocated_on_host, 2),
            "allocated_share": round(allocated_share, 6),
            "idle_share": round(max(0, 1.0 - allocated_share), 6),
        })

    # Previous period comparison
    previous_total_cost = _get_previous_period_cost(db, project_id, policy_version)

    # Active policy info
    policy_row = billing_repo.get_active_policy(db)

    result = {
        **detail,
        "lines": enriched_lines,
        "host_details": host_details,
        "previous_total_cost": previous_total_cost,
        "policy_denominator": policy_row.denominator if policy_row else "allocatable",
        "policy_weight_mode": policy_row.weight_mode if policy_row else "mem",
    }
    return result


def _get_previous_period_cost(db: Session, project_id: str, current_policy_version: int) -> float | None:
    """Get the total_cost of the previous month's bill snapshot, if it exists."""
    from app.models.bill_snapshot import BillSnapshot
    # Find the most recent snapshot before the current period for this project
    prev = db.scalars(
        select(BillSnapshot)
        .where(BillSnapshot.project_id == project_id)
        .order_by(BillSnapshot.period.desc())
        .limit(2)  # current + previous
    ).all()

    if len(prev) >= 2:
        # prev[0] is current, prev[1] is previous
        return prev[1].total_cost
    return None


def _unit_belongs_to_project(db: Session, unit_id: str, project_id: str) -> bool:
    unit = db.get(ConsumingUnit, unit_id)
    return unit is not None and unit.project_id == project_id
