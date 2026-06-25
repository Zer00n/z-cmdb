"""V0.6 unit router — /api/units + /api/hosts"""
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, get_optional_user
from app.core.exceptions import NotFoundError, ValidationError
from app.models.host_resource import HostResource
from app.repositories import host_repo, placement_repo, unit_repo
from app.schemas.consuming_unit import (
    ConsumingUnitCreate,
    ConsumingUnitPatch,
    ConsumingUnitRead,
    PlacementCreate,
    PlacementRead,
)
from app.services import unit_service

router = APIRouter(tags=["units"])

# ── Consuming Unit endpoints ────────────────────────────────────────


@router.post("/api/units", response_model=ConsumingUnitRead, status_code=201)
def create_unit(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    data: ConsumingUnitCreate,
):
    """Create a new consuming unit within a project."""
    return unit_service.create_unit(
        db,
        project_id=data.project_id,
        name=data.name,
        type=data.type,
        owner=data.owner,
        environment=data.environment,
    )


@router.patch("/api/units/{unit_id}", response_model=ConsumingUnitRead)
def patch_unit(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    unit_id: str,
    data: ConsumingUnitPatch,
):
    """Patch only stable fields of a consuming unit."""
    return unit_service.patch_unit(
        db, unit_id,
        name=data.name,
        type=data.type,
        owner=data.owner,
        environment=data.environment,
    )


@router.delete("/api/units/{unit_id}")
def delete_unit(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    unit_id: str,
):
    """Delete a consuming unit (cascades to placements & relations)."""
    from sqlalchemy import delete as sql_delete
    from app.models.placement import Placement
    from app.models.unit_relation import UnitRelation

    unit = unit_repo.get_by_id(db, unit_id)
    # Manual cascade: delete children first (SQLite FK enforcement)
    db.execute(sql_delete(Placement).where(Placement.unit_id == unit_id))
    db.execute(sql_delete(UnitRelation).where(
        (UnitRelation.source_unit_id == unit_id) | (UnitRelation.target_unit_id == unit_id)
    ))
    db.delete(unit)
    db.commit()
    return {"status": "deleted"}


# ── Placement endpoints ─────────────────────────────────────────────


@router.post("/api/units/{unit_id}/placements", response_model=PlacementRead, status_code=201)
def create_placement(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    unit_id: str,
    data: PlacementCreate,
):
    """Create a placement record (declare which host a unit runs on)."""
    # Verify unit exists
    from app.repositories import unit_repo
    unit_repo.get_by_id(db, unit_id)

    # Verify host exists
    host = host_repo.get_by_id(db, data.host_id)

    # Capacity check: warn if requesting more than host total (soft check)
    # (Not blocking — just for future use)

    now = datetime.now(timezone.utc).isoformat()
    return placement_repo.create_placement(
        db,
        unit_id=unit_id,
        host_id=data.host_id,
        cpu_request=data.cpu_request,
        mem_request=data.mem_request,
        instances=data.instances,
        source=data.source,
        observed_at=now,
    )


# ── Host search endpoint ────────────────────────────────────────────


@router.get("/api/hosts/search")
def search_hosts(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[Any, Depends(get_optional_user)],
    q: str = Query(..., min_length=1, description="IP address or hostname keyword"),
):
    """Search hosts by IP (from asset table) or host_resource name.

    Strategy:
      1. Search assets by IP → find or auto-create matching host_resource
      2. Supplement: search host_resource by name (catch any name-keyword hits)
    """
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.asset import Asset
    from app.models.host_resource import HostResource as HR

    results = []

    # 1. Search by asset.ip_address → find or auto-create matching host_resource
    assets = list(
        db.scalars(
            select(Asset).where(Asset.ip_address.like(f"%{q}%")).limit(20)
        ).all()
    )
    seen_host_ids: set[str] = set()
    for asset in assets:
        # Try to find corresponding host_resource by hostname = hr.name
        hr = db.scalars(
            select(HR).where(HR.name == asset.hostname).limit(1)
        ).first()
        # Fallback: match by host_resource.ip_address
        if not hr and asset.ip_address:
            hr = db.scalars(
                select(HR).where(HR.ip_address == asset.ip_address).limit(1)
            ).first()
        # Auto-create host_resource from asset if none exists
        if not hr and asset.ip_address:
            hr_name = asset.hostname or asset.ip_address
            try:
                cpu_val = float(asset.cpu) if asset.cpu else 1.0
            except (ValueError, TypeError):
                cpu_val = 1.0
            mem_mb = float(asset.memory_gb * 1024) if asset.memory_gb else 1024.0
            hr_type = "vm" if asset.asset_type == "virtual" else "physical"
            hr = HR(
                id=str(_uuid.uuid4()),
                name=hr_name,
                ip_address=asset.ip_address,
                type=hr_type,
                cpu_total=cpu_val,
                mem_total=mem_mb,
                monthly_cost=0,
                source="cmdb",
            )
            db.add(hr)
            db.commit()
            db.refresh(hr)
        if hr and hr.id not in seen_host_ids:
            seen_host_ids.add(hr.id)
            results.append({
                "id": hr.id,
                "name": hr.name,
                "ip_address": asset.ip_address,
                "type": hr.type,
                "cpu_total": hr.cpu_total,
                "mem_total": hr.mem_total,
                "monthly_cost": hr.monthly_cost,
            })

    # 2. Supplement: search host_resource by name (includes IP if set)
    hosts = list(
        db.scalars(
            select(HR).where(HR.name.like(f"%{q}%")).order_by(HR.name).limit(20)
        ).all()
    )
    for h in hosts:
        if h.id not in seen_host_ids:
            seen_host_ids.add(h.id)
            # Also try to get IP from asset
            asset = db.scalars(
                select(Asset).where(Asset.hostname == h.name).limit(1)
            ).first()
            results.append({
                "id": h.id,
                "name": h.name,
                "ip_address": asset.ip_address if asset else h.ip_address,
                "type": h.type,
                "cpu_total": h.cpu_total,
                "mem_total": h.mem_total,
                "monthly_cost": h.monthly_cost,
            })

    return results
