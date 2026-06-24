"""V0.6 unit router — /api/units"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.schemas.consuming_unit import ConsumingUnitPatch, ClaimRequest, ConsumingUnitRead
from app.services import unit_service

router = APIRouter(prefix="/api/units", tags=["units"])


@router.patch("/{unit_id}", response_model=ConsumingUnitRead)
def patch_unit(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    unit_id: str,
    data: ConsumingUnitPatch,
):
    """
    Patch only stable fields of a consuming unit.
    Strict allowlist: name, type, owner, environment only.
    Runtime fields (including project_id) are rejected.
    """
    return unit_service.patch_unit(
        db, unit_id,
        name=data.name,
        type=data.type,
        owner=data.owner,
        environment=data.environment,
    )


@router.post("/{unit_id}/claim", response_model=ConsumingUnitRead)
def claim_unit(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
    unit_id: str,
    data: ClaimRequest,
):
    """Claim an unclaimed unit by assigning it to a project."""
    return unit_service.claim_unit(db, unit_id, data.project_id)
