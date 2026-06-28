"""
Vault（SQLite 静态加密）路由：
  GET  /api/lock-status — 当前状态 + 是否需首次 setup
  POST /api/setup       — 首次初始化（仅 needs_setup 时可用），返回一次性恢复码
  POST /api/unlock      — 口令或恢复码解锁

安全：解锁失败统一 401「解锁失败」（key_service 已防用户名枚举）；防爆破锁定 429。
响应中的 recovery_code / admin_password 为一次性凭据，仅经 HTTPS 返回，绝不进日志。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core import keyvault
from app.core.config import settings
from app.schemas.vault import (
    LockStatusResponse,
    SetupRequest,
    SetupResponse,
    UnlockRequest,
    UnlockResponse,
)
from app.services import key_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["vault"])

# 与 auth 路由同名的 refresh cookie（口令解锁后复用登录会话）
REFRESH_COOKIE_NAME = "refresh_token"


@router.get("/api/lock-status", response_model=LockStatusResponse)
def lock_status() -> LockStatusResponse:
    """返回当前加密状态与是否需要首次 setup。"""
    state = keyvault.current_state().value
    return LockStatusResponse(state=state, needs_setup=key_service.needs_setup())


@router.post("/api/setup", response_model=SetupResponse)
def setup(body: SetupRequest) -> SetupResponse:
    """首次初始化：生成 DEK + 入册初始 admin + 恢复码 + 开库迁移。

    仅当 keystore 不存在（needs_setup）时可用；否则 409。
    """
    result = key_service.setup(admin_username=body.username, admin_password=body.password)
    # 不记录恢复码/口令；只记事件
    logger.info("vault setup completed (admin=%s)", result.admin_username)
    return SetupResponse(
        recovery_code=result.recovery_code,
        admin_username=result.admin_username,
        admin_password=result.admin_password,
        message=result.message,
    )


@router.post("/api/unlock", response_model=UnlockResponse)
def unlock(body: UnlockRequest, response: Response) -> UnlockResponse:
    """口令或恢复码解锁。

    口令路径成功后签发 JWT 并设置 refresh cookie（单口令体验）。
    恢复码路径仅切 UNLOCKED（needs_login=True），需再用真实口令登录。
    失败抛 UnlockError（401 统一消息）/ UnlockLockedOutError（429）。
    """
    result = key_service.unlock(
        username=body.username,
        password=body.password,
        recovery_code=body.recovery_code,
    )

    # 口令解锁：设置 refresh cookie（httpOnly），与登录路由一致
    if result.refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=result.refresh_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="strict",
            max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 24 * 3600,
            path="/api/auth",
        )

    return UnlockResponse(
        state=result.state,
        access_token=result.access_token,
        needs_login=result.needs_login,
        username=result.username,
    )
