"""
Application/service inventory data access layer
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
    """Get application record by ID"""
    app = db.get(AssetApp, app_id)
    if app is None:
        raise NotFoundError(f"Application record ID {app_id} not found")
    return app


def list_by_asset(db: Session, asset_id: int) -> list[AssetApp]:
    """List all active applications for an asset"""
    stmt = (
        select(AssetApp)
        .where(AssetApp.asset_id == asset_id, AssetApp.status == "active")
        .order_by(AssetApp.name, AssetApp.version)
    )
    return list(db.scalars(stmt).all())


def create(db: Session, asset_id: int, created_by: int | None = None, **kwargs) -> AssetApp:
    """Create a new application record"""
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
                f"This asset already has an application with the same name and version: {kwargs.get('name')} {kwargs.get('version', '')}"
            )
        raise
    logger.info(
        "asset_app created",
        extra={"app_id": app.id, "asset_id": asset_id, "app_name": app.name},
    )
    return app


def upsert_app(
    db: Session,
    asset_id: int,
    name: str,
    version: str | None = None,
    source: str = "scan",
    created_by: int | None = None,
    **kwargs,
) -> AssetApp:
    """
    Insert or update an application record (idempotent).
    Uses (asset_id, name, version) as the unique key:
    - If it exists: update source / other fields and restore status to active
    - If it does not exist: create a new record
    """
    stmt = select(AssetApp).where(
        AssetApp.asset_id == asset_id,
        AssetApp.name == name,
        AssetApp.version == version,
    )
    app = db.scalar(stmt)
    if app is None:
        app = AssetApp(
            asset_id=asset_id,
            name=name,
            version=version,
            source=source,
            status="active",
            created_by=created_by,
            **kwargs,
        )
        db.add(app)
    else:
        # Update mutable fields
        app.source = source
        app.status = "active"
        for key, value in kwargs.items():
            if hasattr(app, key) and value is not None:
                setattr(app, key, value)
    db.flush()
    logger.info(
        "asset_app upserted",
        extra={"asset_id": asset_id, "app_name": name, "source": source},
    )
    return app


def update(db: Session, app: AssetApp, **kwargs) -> AssetApp:
    """Update an application record"""
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
                f"This asset already has an application with the same name and version: {app.name} {app.version}"
            )
        raise
    return app


def soft_delete(db: Session, app: AssetApp) -> AssetApp:
    """Soft delete: mark as decommissioned"""
    app.status = "decommissioned"
    app.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("asset_app decommissioned", extra={"app_id": app.id})
    return app


def search_global(db: Session, q: str, limit: int = 100) -> list[dict]:
    """
    Global application search: fuzzy match by name or version, return matched apps + associated asset info
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
    """Return all existing application names (deduplicated), used for frontend autocomplete"""
    stmt = (
        select(AssetApp.name)
        .where(AssetApp.status == "active")
        .distinct()
        .order_by(AssetApp.name)
    )
    return list(db.scalars(stmt).all())


def count_by_asset(db: Session, asset_id: int) -> int:
    """Count active applications for an asset"""
    stmt = (
        select(func.count())
        .select_from(AssetApp)
        .where(AssetApp.asset_id == asset_id, AssetApp.status == "active")
    )
    return db.scalar(stmt) or 0


def list_apps_for_assets(db: Session, asset_ids: list[int]) -> dict[int, list[AssetApp]]:
    """
    Batch query active applications for multiple assets, returns {asset_id: [AssetApp, ...]}.
    Avoids N+1 query problem.
    """
    if not asset_ids:
        return {}
    stmt = (
        select(AssetApp)
        .where(AssetApp.asset_id.in_(asset_ids), AssetApp.status == "active")
        .order_by(AssetApp.asset_id, AssetApp.name, AssetApp.version)
    )
    apps = list(db.scalars(stmt).all())
    result: dict[int, list[AssetApp]] = {aid: [] for aid in asset_ids}
    for app in apps:
        result.setdefault(app.asset_id, []).append(app)
    return result
