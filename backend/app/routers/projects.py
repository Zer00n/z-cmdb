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


def _get_or_generate_summary(
    db: Session,
    project_id: str,
    lang: str = "zh",
    force: bool = False,
) -> dict:
    """Core logic: return cached summary or generate via LLM."""
    from datetime import datetime, timezone
    from app.models.project import Project
    from app.engine.summary import generate_project_summary

    project = db.get(Project, project_id)
    if not project:
        return {"error": "Project not found", "status": 404}

    # Return cached summary if available and lang matches (unless force)
    if (
        not force
        and project.summary_lang == lang
        and project.summary_overview
    ):
        return {
            "overview": project.summary_overview,
            "risk": project.summary_risk or "",
            "draft": True,
            "lang": project.summary_lang,
            "generated_at": project.summary_generated_at.isoformat() if project.summary_generated_at else None,
        }

    # Generate new summary via LLM
    try:
        result = generate_project_summary(db, project_id, lang=lang)

        # Persist to DB
        project.summary_overview = result["overview"]
        project.summary_risk = result.get("risk", "")
        project.summary_lang = result.get("lang", lang)
        project.summary_generated_at = datetime.now(timezone.utc)
        db.commit()

        result["generated_at"] = project.summary_generated_at.isoformat()
        return result
    except Exception as e:
        return {
            "overview": None,
            "risk": None,
            "draft": True,
            "degraded": True,
            "reason": f"AI summary unavailable: {e}",
        }


@router.get("/{project_id}/summary")
def get_project_summary(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
    lang: str = Query("zh", description="Output language: zh or en"),
    force: bool = Query(False, description="Force regenerate even if cached"),
):
    """Get AI-generated project summary.
    Returns cached version from DB if available and lang matches.
    Returns 200 with degraded=true if LLM unavailable (normal degradation, not an error)."""
    result = _get_or_generate_summary(db, project_id, lang=lang, force=force)
    if result.get("status") == 404:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": result["error"]})
    return result


@router.post("/{project_id}/summary/regenerate")
def regenerate_project_summary(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    project_id: str,
    lang: str = Query("zh", description="Output language: zh or en"),
):
    """Force regenerate AI summary (bypasses cache)."""
    result = _get_or_generate_summary(db, project_id, lang=lang, force=True)
    if result.get("status") == 404:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": result["error"]})
    return result
