"""
LOCKED 态路由拦截中间件（PRD §4 状态机）

应用以 LOCKED 启动（keyvault），DEK 不在内存、DB 引擎未建。此时仅放行：
  - 所有非 ``/api/*`` 请求（前端静态资源 + 解锁页 SPA）
  - ``/api/health``、``/api/lock-status``
  - ``/api/unlock*``、``/api/setup*``
  - CORS 预检 OPTIONS

其余 ``/api/*`` 一律返回 ``423 Locked``，由前端引导至解锁页。
UNLOCKED 态放行全部。

注意：中间件注册顺序需保证本拦截在业务路由之前生效（见 main.py）。
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core import keyvault

# LOCKED 态放行的精确 API 路径
_ALLOWED_API_EXACT = {"/api/health", "/api/lock-status"}
# LOCKED 态放行的 API 前缀
_ALLOWED_API_PREFIXES = ("/api/unlock", "/api/setup")


class LockGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if keyvault.is_unlocked():
            return await call_next(request)

        path = request.url.path
        method = request.method

        # CORS 预检始终放行（否则浏览器跨域被锁死）
        if method == "OPTIONS":
            return await call_next(request)

        # 非 API（静态资源、解锁页 SPA、根路径）一律放行
        if not path.startswith("/api/"):
            return await call_next(request)

        # 白名单 API 放行
        if path in _ALLOWED_API_EXACT or path.startswith(_ALLOWED_API_PREFIXES):
            return await call_next(request)

        # 其余 API：423 Locked
        return JSONResponse(
            status_code=423,
            content={
                "error_code": "VAULT_LOCKED",
                "message": "Database is locked. Unlock is required before accessing this resource.",
            },
            headers={"Retry-After": "0"},
        )
