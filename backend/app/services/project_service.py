"""V0.6 project service"""
import calendar
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories import project_repo, billing_repo


def list_projects(
    db: Session,
    search: str | None = None,
    business_unit: str | None = None,
    owner: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    projects, total = project_repo.list_projects(db, search, business_unit, owner, page, page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)

    now = datetime.now(timezone.utc)
    current_period = f"{now.year}-{now.month:02d}"

    items = []
    for p in projects:
        unit_count = project_repo.get_unit_count(db, p.id)
        host_count = project_repo.get_host_count(db, p.id)

        # Current month cost: read from bill_snapshot if billing enabled
        current_month_cost = None
        if p.billing_enabled:
            snapshot = billing_repo.get_bill_snapshot(db, p.id, current_period)
            if snapshot:
                current_month_cost = snapshot.total_cost

        items.append({
            "id": p.id,
            "name": p.name,
            "business_unit": p.business_unit,
            "owner": p.owner,
            "billing_enabled": p.billing_enabled,
            "unit_count": unit_count,
            "host_count": host_count,
            "current_month_cost": current_month_cost,
            "updated_at": p.updated_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_project(db: Session, project_id: str) -> Project:
    return project_repo.get_by_id(db, project_id)


def create_project(db: Session, name: str, owner: str | None = None,
                   business_unit: str | None = None) -> Project:
    return project_repo.create_project(db, name=name, owner=owner, business_unit=business_unit)


def update_project(db: Session, project_id: str, **kwargs) -> Project:
    project = project_repo.get_by_id(db, project_id)
    return project_repo.update_project(db, project, **kwargs)


def get_project_units(db: Session, project_id: str) -> list[dict]:
    """Get consuming units with current runtime info."""
    from app.repositories import unit_repo, placement_repo

    units = unit_repo.list_by_project(db, project_id)
    result = []
    for u in units:
        placement = placement_repo.get_current_placement(db, u.id)
        item = {
            "id": u.id,
            "project_id": u.project_id,
            "name": u.name,
            "type": u.type,
            "owner": u.owner,
            "environment": u.environment,
            "created_at": u.created_at,
            "updated_at": u.updated_at,
        }
        if placement:
            item["runtime"] = {
                "instances": placement.instances,
                "cpu": placement.cpu_request,
                "mem": placement.mem_request,
                "source": placement.source,
                "observed_at": placement.observed_at,
            }
        result.append(item)
    return result
