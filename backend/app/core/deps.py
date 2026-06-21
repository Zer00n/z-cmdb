"""
FastAPI dependency injection
get_current_user + role-check dependencies
"""
import logging
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.models.user import User
from app.repositories import user_repo

logger = logging.getLogger(__name__)


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    """
    Parse the current user from Authorization: Bearer <token>.
    Raises AuthenticationError on failure (global handler returns 401).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing authentication token")

    token = authorization[len("Bearer "):]
    payload = decode_token(token, expected_type="access")

    user_id = int(payload["sub"])
    user = user_repo.get_by_id(db, user_id)

    if user.status == "disabled":
        raise AuthenticationError("Account has been disabled")

    return user


# ── Role-check dependencies ─────────────────────────────────────


def require_super_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Accessible by super_admin only"""
    if current_user.role != "super_admin":
        raise PermissionDeniedError("Requires super admin privileges")
    return current_user


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Accessible by super_admin and admin"""
    if current_user.role not in ("super_admin", "admin"):
        raise PermissionDeniedError("Requires admin privileges")
    return current_user


def require_auditor(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Auditor role only"""
    if current_user.role != "auditor":
        raise PermissionDeniedError("Requires auditor privileges")
    return current_user


def require_any(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Accessible by any authenticated user"""
    return current_user


# ── Type aliases for convenient route usage ──────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
AdminUser = Annotated[User, Depends(require_admin)]
AuditorUser = Annotated[User, Depends(require_auditor)]
AnyUser = Annotated[User, Depends(require_any)]


def require_auditor_exists(
    db: Session = Depends(get_db),
) -> None:
    """
    PRD 3.3: At least one auditor account must be created to unlock full functionality.
    Checked before critical operations (scan upload, topology generation, report export).
    """
    from app.services.config_service import has_auditor_user
    if not has_auditor_user(db):
        raise PermissionDeniedError(
            "No auditor account exists. Please create at least one auditor user in user management before using full functionality."
        )


AuditorExists = Annotated[None, Depends(require_auditor_exists)]


# ── V0.4 cost accounting feature toggle dependency ───────────────


def _require_cost_feature(
    db: Session = Depends(get_db),
) -> None:
    """Centralized cost accounting feature toggle check; raises FeatureDisabledError when off.
    All cost/billing/rate/relation routes attach this dependency to avoid per-endpoint duplication."""
    from app.services.config_service import is_cost_accounting_enabled
    from app.core.exceptions import FeatureDisabledError
    if not is_cost_accounting_enabled(db):
        raise FeatureDisabledError("Asset cost accounting is not enabled. Please enable it in system configuration.")


RequireCostFeature = Annotated[None, Depends(_require_cost_feature)]
