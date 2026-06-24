"""V0.6 host resource repository"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import HostNotFoundError
from app.models.host_resource import HostResource


def get_by_id(db: Session, host_id: str) -> HostResource:
    host = db.get(HostResource, host_id)
    if not host:
        raise HostNotFoundError(f"Host resource {host_id} not found")
    return host


def list_by_ids(db: Session, host_ids: set[str]) -> list[HostResource]:
    if not host_ids:
        return []
    return list(
        db.scalars(
            select(HostResource)
            .where(HostResource.id.in_(host_ids))
            .order_by(HostResource.id)
        ).all()
    )


def list_all(db: Session) -> list[HostResource]:
    return list(db.scalars(select(HostResource).order_by(HostResource.id)).all())
