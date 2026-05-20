"""
FastAPI 应用入口
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import CMDBException
from app.core.logging import setup_logging
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.assets import router as assets_router
from app.routers.scans import router as scans_router
from app.routers.audit import router as audit_router
from app.routers.users import router as users_router
from app.routers.reports import router as reports_router
from app.routers.config import router as config_router
from app.routers.topology import router as topology_router
from app.routers.asset_apps import router as asset_apps_router

# 初始化日志（必须在其他模块 import 之前）
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 安全头中间件（CSP + 其他）────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://embed.diagrams.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "frame-src https://embed.diagrams.net; "
        "connect-src 'self' https://embed.diagrams.net; "
        "font-src 'self' data:;"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── 全局异常处理器 ───────────────────────────────────────────


@app.exception_handler(CMDBException)
async def cmdb_exception_handler(request: Request, exc: CMDBException) -> JSONResponse:
    """统一处理所有业务异常，Router 层不需要写 try/except"""
    logger.warning(
        "business exception: %s",
        exc.message,
        extra={
            "error_code": exc.error_code,
            "exc_message": exc.message,  # 避免与 LogRecord 保留字 'message' 冲突
            "path": str(request.url),
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：未预期的异常，返回 500"""
    logger.error(
        "unhandled exception",
        extra={"path": str(request.url), "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "服务器内部错误"},
    )


# ── 路由注册 ─────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(scans_router)
app.include_router(audit_router)
app.include_router(users_router)
app.include_router(reports_router)
app.include_router(config_router)
app.include_router(topology_router)
app.include_router(asset_apps_router)


# ── 启动事件 ─────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "application starting",
        extra={"env": settings.APP_ENV, "version": settings.APP_VERSION},
    )

    # 测试环境跳过初始化（由测试自行控制数据）
    if settings.APP_ENV == "testing":
        return

    from app.core.database import SessionLocal
    from app.services.auth_service import ensure_initial_admin

    # 首次启动：若 users 表为空则创建初始 admin 账号
    with SessionLocal() as db:
        ensure_initial_admin(db)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("application shutting down")
