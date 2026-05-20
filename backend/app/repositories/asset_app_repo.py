"""
应用服务清单数据访问层
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, DuplicateError
from app.models.asset import Asset
from app.models.asset_app import AssetApp

logger = logging.getLogger(__name__)


def get_by_id(db: Session, app_id: int) -> AssetApp:
    """根据 ID 获取应用记录"""
    app = db.get(AssetApp, app_id)
    if app is None:
        raise NotFoundError(f"应用记录 ID {app_id} 不存在")
    return app


def list_by_asset(db: Session, asset_id: int) -> list[AssetApp]:
    """列出某资产的所有 active 应用"""
    stmt = (
        select(AssetApp)
        .where(AssetApp.asset_id == asset_id, AssetApp.status == "active")
        .order_by(AssetApp.name, AssetApp.version)
    )
    return list(db.scalars(stmt).all())


def create(db: Session, asset_id: int, created_by: int | None = None, **kwargs) -> AssetApp:
    """新增应用记录"""
    app = AssetApp(
        asset_id=asset_id,
        created_by=created_by,
        **kwargs,
    )
    db.add(app)
    try:
        db.flush()
    except Exception as e:
        db.rollback()
        if "UNIQUE constraint failed" in str(e) or "uq_asset_app_name_version" in str(e):
            raise DuplicateError(
                f"该资产已存在同名同版本的应用: {kwargs.get('name')} {kwargs.get('version', '')}"
            )
        raise
    logger.info(
        "asset_app created",
        extra={"app_id": app.id, "asset_id": asset_id, "name": app.name},
    )
    return app


def update(db: Session, app: AssetApp, **kwargs) -> AssetApp:
    """更新应用记录"""
    for key, value in kwargs.items():
        if hasattr(app, key) and value is not None:
            setattr(app, key, value)
    app.updated_at = datetime.now(timezone.utc)
    try:
        db.flush()
    except Exception as e:
        db.rollback()
        if "UNIQUE constraint failed" in str(e) or "uq_asset_app_name_version" in str(e):
            raise DuplicateError(
                f"该资产已存在同名同版本的应用: {app.name} {app.version}"
            )
        raise
    return app


def soft_delete(db: Session, app: AssetApp) -> AssetApp:
    """软删除：标记为 decommissioned"""
    app.status = "decommissioned"
    app.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("asset_app decommissioned", extra={"app_id": app.id})
    return app


def search_global(db: Session, q: str, limit: int = 100) -> list[dict]:
    """
    全局应用搜索：按 name 或 version 模糊匹配，返回命中的应用 + 关联资产信息
    """
    kw = f"%{q}%"
    stmt = (
        select(
            AssetApp.id,
            AssetApp.asset_id,
            AssetApp.name,
            AssetApp.version,
            AssetApp.category,
            AssetApp.port,
            Asset.asset_no,
            Asset.ip_address,
            Asset.hostname,
        )
        .join(Asset, AssetApp.asset_id == Asset.id)
        .where(
            AssetApp.status == "active",
            or_(
                AssetApp.name.like(kw),
                AssetApp.version.like(kw),
            ),
        )
        .order_by(AssetApp.name, Asset.ip_address)
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.id,
            "asset_id": r.asset_id,
            "name": r.name,
            "version": r.version,
            "category": r.category,
            "port": r.port,
            "asset_no": r.asset_no,
            "ip_address": r.ip_address,
            "hostname": r.hostname,
        }
        for r in rows
    ]


def get_all_names(db: Session) -> list[str]:
    """返回所有已存在的应用名（去重），用于前端 autocomplete"""
    stmt = (
        select(AssetApp.name)
        .where(AssetApp.status == "active")
        .distinct()
        .order_by(AssetApp.name)
    )
    return list(db.scalars(stmt).all())


def count_by_asset(db: Session, asset_id: int) -> int:
    """统计某资产的 active 应用数量"""
    stmt = (
        select(func.count())
        .select_from(AssetApp)
        .where(AssetApp.asset_id == asset_id, AssetApp.status == "active")
    )
    return db.scalar(stmt) or 0
