"""
FastAPI application entry point
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
from app.routers.dashboard import router as dashboard_router
from app.routers.features import router as features_router
from app.routers.departments import router as departments_router
from app.routers.cost import router as cost_router
from app.routers.billing import router as billing_router
from app.routers.cost_rates import router as cost_rates_router
from app.routers.asset_relations import router as asset_relations_router
from app.routers.asset_cost_details import router as asset_cost_details_router
from app.routers.import_presets import router as import_presets_router

# Initialize logging (must be done before other module imports)
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


# ── Security headers middleware (CSP + others) ────────────────
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
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── Global exception handlers ────────────────────────────────


@app.exception_handler(CMDBException)
async def cmdb_exception_handler(request: Request, exc: CMDBException) -> JSONResponse:
    """Unified handler for all business exceptions; routers don't need to write try/except"""
    logger.warning(
        "business exception: %s",
        exc.message,
        extra={
            "error_code": exc.error_code,
            "exc_message": exc.message,  # Avoid conflict with LogRecord reserved field 'message'
            "path": str(request.url),
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: unexpected exceptions, returns 500"""
    logger.error(
        "unhandled exception",
        extra={"path": str(request.url), "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "Internal server error"},
    )


# ── Route registration ────────────────────────────────────────
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
app.include_router(dashboard_router)
app.include_router(features_router)
app.include_router(departments_router)
app.include_router(cost_router)
app.include_router(billing_router)
app.include_router(cost_rates_router)
app.include_router(asset_relations_router)
app.include_router(asset_cost_details_router)
app.include_router(import_presets_router)


# ── Startup event ─────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "application starting",
        extra={"env": settings.APP_ENV, "version": settings.APP_VERSION},
    )

    # 生产环境密钥校验
    from app.core.config import validate_runtime_secrets
    validate_runtime_secrets()

    # CORS 配置安全告警
    if "*" in settings.CORS_ORIGINS:
        logger.warning(
            "CORS_ORIGINS contains '*' while credentials are allowed; "
            "this is unsafe in production. Set explicit origins."
        )
    if settings.APP_ENV.lower() in ("production", "prod"):
        _insecure = [o for o in settings.CORS_ORIGINS if o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o]
        if _insecure:
            logger.warning("CORS origins over plain HTTP in production: %s", _insecure)

    # Skip initialization in testing environment (test data is managed independently)
    if settings.APP_ENV == "testing":
        return

    from app.core.database import SessionLocal
    from app.services.auth_service import ensure_initial_admin

    # First startup: create initial admin account if users table is empty
    with SessionLocal() as db:
        ensure_initial_admin(db)

    # 若初始明文密码文件仍存在，提醒尽快改密
    from app.core.config import settings as _settings
    _pw_file = _settings.db_path.parent / "INITIAL_ADMIN_PASSWORD.txt"
    if _pw_file.exists():
        logger.warning(
            "INITIAL_ADMIN_PASSWORD.txt still present on disk; "
            "change the admin password to auto-remove it"
        )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("application shutting down")
