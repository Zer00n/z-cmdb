"""V0.6 unit service"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.consuming_unit import ConsumingUnit
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


_ALLOWED_PATCH_FIELDS = {"name", "type", "owner", "environment"}


def patch_unit(db: Session, unit_id: str, **kwargs) -> ConsumingUnit:
    """Patch only stable fields (strict allowlist)."""
    unit = unit_repo.get_by_id(db, unit_id)
    updates = {k: v for k, v in kwargs.items() if k in _ALLOWED_PATCH_FIELDS}
    if updates:
        return unit_repo.update_unit(db, unit, **updates)
    return unit
