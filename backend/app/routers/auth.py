"""
Authentication routes
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
POST /api/auth/change-password
"""
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, Cookie
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import AnyUser
from app.schemas.user import ChangePasswordRequest, LoginRequest, TokenResponse
from app.services import auth_service, audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Refresh cookie name
REFRESH_COOKIE_NAME = "refresh_token"


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    User login.
    Returns access_token (JSON body) and sets refresh_token (httpOnly cookie).
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]

    try:
        access_token, refresh_token = auth_service.login(db, body.username, body.password)
    except Exception as exc:
        # Log failed login to audit trail
        audit_service.log_action(
            db, action_type="LOGIN", target_type="session",
            details={"username": body.username, "reason": str(exc)},
            result="failed", ip_address=ip, user_agent=ua,
        )
        db.commit()
        raise

    # Log successful login
    from app.repositories import user_repo
    user = user_repo.get_by_username(db, body.username)
    audit_service.log_action(
        db, action_type="LOGIN", user=user, target_type="session",
        details={"username": body.username},
        result="success", ip_address=ip, user_agent=ua,
    )
    db.commit()

    # Check if password change is required: first login (password_changed_at is None) or older than 90 days
    must_change = False
    if user:
        if user.password_changed_at is None:
            must_change = True
        else:
            from datetime import timedelta
            age = datetime.now(timezone.utc) - user.password_changed_at.replace(tzinfo=timezone.utc) if user.password_changed_at.tzinfo is None else datetime.now(timezone.utc) - user.password_changed_at
            if age > timedelta(days=90):
                must_change = True

    # Set refresh_token as httpOnly cookie
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 3600,
        path="/api/auth",
    )

    return TokenResponse(access_token=access_token, must_change_password=must_change)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Use refresh_token cookie to obtain a new access_token.
    """
    from app.core.exceptions import AuthenticationError

    if not refresh_token:
        raise AuthenticationError("refresh_token is missing")

    new_access_token = auth_service.refresh_access_token(db, refresh_token)
    return TokenResponse(access_token=new_access_token)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Logout: clear the refresh_token cookie.
    """
    # Audit log
    audit_service.log_from_request(
        db, request, action_type="LOGIN", user=current_user,
        target_type="session", details={"action": "logout"},
    )
    db.commit()

    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth",
        samesite="strict",
    )
    return {"message": "Logged out successfully"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: AnyUser,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Change the current user's password (requires authentication).
    """
    auth_service.change_password(db, current_user, body.old_password, body.new_password)

    # Audit log
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="user", target_id=current_user.id,
        details={"action": "change_password"},
    )
    db.commit()

    return {"message": "Password changed successfully"}
