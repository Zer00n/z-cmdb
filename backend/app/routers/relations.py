"""V0.6 unit relation router — /api/relations"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.schemas.consuming_unit import RelationCreate, RelationRead
from app.services import relation_service

router = APIRouter(prefix="/api/relations", tags=["relations"])


@router.post("", response_model=RelationRead, status_code=201)
def create_relation(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    data: RelationCreate,
):
    """Create a dependency edge between two consuming units."""
    return relation_service.create_relation(
        db,
        source_unit_id=data.source_unit_id,
        target_unit_id=data.target_unit_id,
        rel_type=data.rel_type,
    )


@router.delete("/{relation_id}", status_code=204)
def delete_relation(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    relation_id: str,
):
    """Delete a dependency edge."""
    relation_service.delete_relation(db, relation_id)
    return None
