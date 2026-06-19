"""
鉴权路由
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

# refresh cookie 名称
REFRESH_COOKIE_NAME = "refresh_token"


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    用户登录。
    返回 access_token（JSON body）+ 设置 refresh_token（httpOnly cookie）。
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]

    try:
        access_token, refresh_token = auth_service.login(db, body.username, body.password)
    except Exception as exc:
        # 登录失败也要记录审计日志
        audit_service.log_action(
            db, action_type="LOGIN", target_type="session",
            details={"username": body.username, "reason": str(exc)},
            result="failed", ip_address=ip, user_agent=ua,
        )
        db.commit()
        raise

    # 登录成功审计
    from app.repositories import user_repo
    user = user_repo.get_by_username(db, body.username)
    audit_service.log_action(
        db, action_type="LOGIN", user=user, target_type="session",
        details={"username": body.username},
        result="success", ip_address=ip, user_agent=ua,
    )
    db.commit()

    # 判断是否需要强制改密：首次登录（password_changed_at 为空）或超过 90 天
    must_change = False
    if user:
        if user.password_changed_at is None:
            must_change = True
        else:
            from datetime import timedelta
            age = datetime.now(timezone.utc) - user.password_changed_at.replace(tzinfo=timezone.utc) if user.password_changed_at.tzinfo is None else datetime.now(timezone.utc) - user.password_changed_at
            if age > timedelta(days=90):
                must_change = True

    # refresh_token 写入 httpOnly cookie
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
    用 refresh_token cookie 换新的 access_token。
    """
    from app.core.exceptions import AuthenticationError

    if not refresh_token:
        raise AuthenticationError("缺少 refresh_token")

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
    注销：清除 refresh_token cookie。
    """
    # 审计日志
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
    return {"message": "已退出登录"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: AnyUser,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    修改当前用户密码（需要登录）。
    """
    auth_service.change_password(db, current_user, body.old_password, body.new_password)

    # 审计日志
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="user", target_id=current_user.id,
        details={"action": "change_password"},
    )
    db.commit()

    return {"message": "密码修改成功"}
