"""V0.6 unit service"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.project import Project
from app.repositories import unit_repo


def create_unit(
    db: Session,
    project_id: str,
    name: str,
    type: str,
    owner: str | None = None,
    environment: str | None = None,
):
    """Create a new consuming unit and assign it to a project."""
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project {project_id} not found")
    return unit_repo.create_unit(
        db,
        project_id=project_id,
        name=name,
        type=type,
        owner=owner,
        environment=environment,
    )


def patch_unit(
    db: Session, unit_id: str,
    name: str | None = None,
    type: str | None = None,
    owner: str | None = None,
    environment: str | None = None,
):
    """Patch only stable fields (strict allowlist)."""
    unit = unit_repo.get_by_id(db, unit_id)
    updates = {}
    if name is not None:
        updates["name"] = name
    if type is not None:
        updates["type"] = type
    if owner is not None:
        updates["owner"] = owner
    if environment is not None:
        updates["environment"] = environment
    if updates:
        return unit_repo.update_unit(db, unit, **updates)
    return unit
