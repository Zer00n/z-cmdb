"""
Feature flag API
GET /api/features   Returns enabled state for each feature domain (not restricted by feature flags themselves)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.services.config_service import is_cost_accounting_enabled

router = APIRouter(tags=["features"])


@router.get("/api/features")
def get_features(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Return feature flag states, used by frontend to decide which entries to render at startup"""
    return {
        "cost_accounting": is_cost_accounting_enabled(db),
    }
