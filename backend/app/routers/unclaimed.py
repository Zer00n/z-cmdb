"""V0.6 unclaimed resources router — /api/unclaimed"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.schemas.billing_policy import (
    UnclaimedResponse,
    UnclaimedUnitRead,
    ZombieHostRead,
    UnclaimedSummary,
)
from app.services import unclaimed_service

router = APIRouter(prefix="/api/unclaimed", tags=["unclaimed"])


@router.get("", response_model=UnclaimedResponse)
def get_unclaimed(
    db: Annotated[Session, Depends(get_db)],
    _user: AnyUser,
):
    """Get unclaimed resources: units without project + zombie hosts."""
    result = unclaimed_service.get_unclaimed_resources(db)

    units = []
    for u in result["unclaimed_units"]:
        units.append(UnclaimedUnitRead(
            id=u.id, name=u.name, type=u.type, owner=u.owner,
            environment=u.environment, created_at=u.created_at,
        ))

    zombies = []
    for h in result["zombie_hosts"]:
        zombies.append(ZombieHostRead(
            id=h.id, name=h.name, type=h.type,
            cpu_total=h.cpu_total, mem_total=h.mem_total,
            monthly_cost=h.monthly_cost, source=h.source,
            created_at=h.created_at,
        ))

    return UnclaimedResponse(
        unclaimed_units=units,
        zombie_hosts=zombies,
        summary=UnclaimedSummary(**result["summary"]),
    )
