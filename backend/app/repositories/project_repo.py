"""V0.6 project repository"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ProjectNotFoundError
from app.models.consuming_unit import ConsumingUnit
from app.models.host_resource import HostResource
from app.models.placement import Placement
from app.models.project import Project


def get_by_id(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise ProjectNotFoundError(f"Project {project_id} not found")
    return project


def list_projects(
    db: Session,
    search: str | None = None,
    business_unit: str | None = None,
    owner: str | None = None,
    department: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Project], int]:
    stmt = select(Project)
    if search:
        stmt = stmt.where(Project.name.contains(search))
    if business_unit:
        stmt = stmt.where(Project.business_unit == business_unit)
    if owner:
        stmt = stmt.where(Project.owner == owner)
    if department:
        stmt = stmt.where(Project.department == department)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Paginate
    stmt = stmt.order_by(Project.id).offset((page - 1) * page_size).limit(page_size)
    projects = list(db.scalars(stmt).all())
    return projects, total


def get_unit_count(db: Session, project_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(ConsumingUnit).where(
            ConsumingUnit.project_id == project_id
        )
    ) or 0


def get_host_count(db: Session, project_id: str) -> int:
    """Count distinct hosts that have placements for units of this project."""
    return db.scalar(
        select(func.count(func.distinct(Placement.host_id)))
        .join(ConsumingUnit, ConsumingUnit.id == Placement.unit_id)
        .where(ConsumingUnit.project_id == project_id)
    ) or 0


def create_project(db: Session, **kwargs) -> Project:
    project = Project(**kwargs)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, **kwargs) -> Project:
    for key, value in kwargs.items():
        if value is not None:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()


def list_distinct_departments(db: Session) -> list[str]:
    """Return sorted list of distinct non-empty department values."""
    return list(
        db.scalars(
            select(Project.department)
            .where(Project.department.isnot(None), Project.department != "")
            .distinct()
            .order_by(Project.department)
        ).all()
    )
