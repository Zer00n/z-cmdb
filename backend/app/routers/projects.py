"""V0.6 project router — /api/projects"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, AdminUser
from app.engine.topology import generate_topology
from app.schemas.project import ProjectCreate, ProjectListItem, ProjectListResponse, ProjectRead, ProjectUpdate
from app.schemas.consuming_unit import ConsumingUnitRead
from app.schemas.billing_policy import BillSnapshotRead
from app.services import project_service, bill_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    search: str | None = Query(None),
    business_unit: str | None = Query(None),
    owner: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List projects with aggregated metrics."""
    return project_service.list_projects(db, search, business_unit, owner, page, page_size)


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    db: Annotated[Session, Depends(get_db)],
    _user: AdminUser,
    data: ProjectCreate,
):
    """Create a new project."""
    return project_service.create_project(db, name=data.name, owner=data.owner, business_unit=data.business_unit)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
):
    """Get project details."""
    return project_service.get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    db: Annotated[Session, Depends(get_db)],
    _user: AdminUser,
    project_id: str,
    data: ProjectUpdate,
):
    """Update project (only name/owner/business_unit/billing_enabled)."""
    updates = data.model_dump(exclude_unset=True)
    return project_service.update_project(db, project_id, **updates)


@router.get("/{project_id}/topology")
def get_topology(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
):
    """Get deterministic topology data for a project."""
    return generate_topology(db, project_id)


@router.get("/{project_id}/units")
def get_project_units(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
):
    """Get consuming units with current runtime info for a project."""
    return project_service.get_project_units(db, project_id)


@router.get("/{project_id}/bill")
def get_project_bill(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
    period: str = Query(..., description="Billing period YYYY-MM"),
):
    """Get or generate bill snapshot for a project and period."""
    return bill_service.get_or_generate_bill(db, project_id, period)


@router.get("/{project_id}/summary")
def get_project_summary(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
):
    """Get AI-generated project summary (draft). Returns 503 if LLM unavailable."""
    from app.engine.summary import generate_project_summary
    try:
        return generate_project_summary(db, project_id)
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"error": f"AI summary unavailable: {str(e)}"},
        )
