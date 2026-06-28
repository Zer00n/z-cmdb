"""
FastAPI application entry point
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import CMDBException
from app.core.logging import setup_logging
from app.middleware.lock_gate import LockGateMiddleware
from app.routers.health import router as health_router
from app.routers.unlock import router as unlock_router
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
# V0.6 project-perspective routers
from app.routers.projects import router as projects_router
from app.routers.units import router as units_router
from app.routers.billing_policy import router as billing_policy_router
from app.routers.relations import router as relations_router

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
# 中间件执行顺序（外→内）：security_headers → CORS → lock_gate → 路由
# lock_gate 必须在 CORS 内层，使其 423 响应也能带上 CORS 头（跨域可读）。
app.add_middleware(LockGateMiddleware)
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
    # ExcelParseError carries detailed row-level errors
    content: dict = {"error_code": exc.error_code, "message": exc.message}
    if hasattr(exc, "errors") and exc.errors:
        content["errors"] = exc.errors

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
        content=content,
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
app.include_router(unlock_router)
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
# V0.6 project-perspective routers
app.include_router(projects_router)
app.include_router(units_router)
app.include_router(billing_policy_router)
app.include_router(relations_router)


# ── Static hosting + SPA fallback (production single-port) ──────
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = (Path(__file__).resolve().parent.parent / "static")

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # API paths must NOT be swallowed — return JSON 404
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Serve real static files directly
        candidate = (STATIC_DIR / full_path).resolve()
        if STATIC_DIR in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        # All other paths → index.html (Vue Router history mode)
        return FileResponse(STATIC_DIR / "index.html")


# ── Startup event ─────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    import os

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

    # 加密模型（PRD §6）：应用以 LOCKED 启动 —— 引擎/迁移/初始 admin 全部不在
    # 启动期完成，改由 setup / 解锁后执行。
    from app.core import keyvault
    from app.services import key_service

    logger.info("vault is LOCKED at startup; awaiting setup/unlock")

    # ── 加密状态提醒（print，确保 console / journal / docker logs 可见）──
    _print_vault_banner(key_service)

    # 无人值守（systemd/Docker）：CMDB_UNLOCK_PASSWORD 注入自动解锁（PRD §6）。
    # 该变量绝不写入 .env，由运维在启动时注入，用后立即从环境清除。
    unlock_pw = os.environ.get("CMDB_UNLOCK_PASSWORD")
    unlock_user = os.environ.get("CMDB_UNLOCK_USER", "admin")
    if unlock_pw:
        try:
            if key_service.needs_setup():
                logger.warning(
                    "CMDB_UNLOCK_PASSWORD is set but vault needs initial setup; "
                    "auto-unlock skipped — complete setup first."
                )
            else:
                _try_auto_unlock(key_service, unlock_user, unlock_pw)
        except Exception as exc:  # noqa: BLE001
            logger.error("auto-unlock via CMDB_UNLOCK_PASSWORD failed: %s", exc)
        finally:
            # 无论成败，立即从环境清除口令，绝不留存（操作指南 §0.1）
            os.environ.pop("CMDB_UNLOCK_PASSWORD", None)
            os.environ.pop("CMDB_UNLOCK_USER", None)

    # ── 最终状态 ──
    if keyvault.is_unlocked():
        print(f"  [OK] 已解锁并就绪")
    else:
        print(f"  [LOCKED] 仍在锁定状态，等待浏览器解锁")
    print(f"{'='*60}\n")


def _print_vault_banner(key_service) -> None:
    """启动时的加密状态提醒（print 确保 console / journal / docker logs 可见）。"""
    from app.core import database, keyvault
    from app.core.config import settings

    _db = settings.db_path
    _ks = key_service.keystore_path()

    print(f"\n{'='*60}")
    print(f"  Z-CMDB v{settings.APP_VERSION} — 数据库加密已启用")
    print(f"{'='*60}")
    print(f"  访问地址 : http://localhost:8000")
    print(f"  数据库   : {_db}")
    print(f"  密钥信封 : {_ks}")

    if key_service.needs_setup():
        print(f"\n  [首次部署] 数据库尚未初始化，请在浏览器完成 Setup：")
        print(f"    1. 设置管理员用户名和口令（>=12位，含大小写+数字+特殊字符）")
        print(f"    2. 系统会生成一次性恢复码 —— 务必立即离线保存！")
        print(f"    3. 恢复码是所有口令丢失时的唯一出路，丢失 = 数据永久不可读")
    else:
        print(f"\n  [已加密] 数据库已锁定，请解锁后使用：")
        print(f"    - 浏览器打开后输入管理员口令解锁")
        print(f"    - 或设置 CMDB_UNLOCK_PASSWORD 环境变量自动解锁")
        print(f"\n  [!] 请确认已备份以下文件：")
        print(f"    - {_db}       （加密数据库）")
        print(f"    - {_ks} （密钥信封，丢失=数据不可读）")
        print(f"    - .env               （JWT 密钥配置）")


def _try_auto_unlock(key_service, username: str, secret: str) -> None:
    """无人值守自动解锁：先按恢复码，失败再按用户口令。"""
    from app.core.exceptions import UnlockError

    try:
        key_service.unlock(recovery_code=secret)
        logger.info("auto-unlocked via CMDB_UNLOCK_PASSWORD (recovery code)")
        return
    except UnlockError:
        pass
    try:
        key_service.unlock(username=username, password=secret)
        logger.info("auto-unlocked via CMDB_UNLOCK_PASSWORD (user=%s)", username)
    except UnlockError as exc:
        logger.error("auto-unlock failed for user=%s: %s", username, exc)
        raise


@app.on_event("shutdown")
async def on_shutdown() -> None:
    from app.core import keyvault, database
    keyvault.lock()
    database.shutdown_engine()
    logger.info("application shutting down")
