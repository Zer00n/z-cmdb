"""
Application inventory business logic
"""
import csv
import io
import logging

from sqlalchemy.orm import Session

from app.models.asset_app import AssetApp
from app.repositories import asset_app_repo, asset_repo
from app.schemas.asset_app import (
    AssetAppCreate,
    AssetAppListResponse,
    AssetAppRead,
    AssetAppUpdate,
    AppSearchResponse,
    AppSearchItem,
)

logger = logging.getLogger(__name__)


def list_apps(db: Session, asset_id: int) -> AssetAppListResponse:
    """List all applications for an asset"""
    # Confirm the asset exists
    asset_repo.get_by_id(db, asset_id)
    apps = asset_app_repo.list_by_asset(db, asset_id)
    return AssetAppListResponse(
        items=[AssetAppRead.model_validate(a) for a in apps],
        total=len(apps),
    )


def create_app(db: Session, asset_id: int, data: AssetAppCreate, created_by: int | None = None) -> AssetAppRead:
    """Add a new application; if a port is provided, also sync it to asset_ports"""
    # Confirm the asset exists
    asset_repo.get_by_id(db, asset_id)
    app = asset_app_repo.create(
        db,
        asset_id=asset_id,
        created_by=created_by,
        name=data.name,
        version=data.version,
        category=data.category,
        port=data.port,
        protocol=data.protocol,
        install_path=data.install_path,
        config_path=data.config_path,
        notes=data.notes,
    )
    # Sync port: if the app has a port, upsert it into the asset_ports table
    if data.port:
        asset_repo.upsert_port(
            db,
            asset_id=asset_id,
            port_number=data.port,
            protocol=data.protocol or "tcp",
            service_name=data.name,
            service_version=data.version,
            state="open",
        )
    db.commit()
    return AssetAppRead.model_validate(app)


def update_app(db: Session, asset_id: int, app_id: int, data: AssetAppUpdate) -> AssetAppRead:
    """Update an application; if the port changes, also update asset_ports"""
    # Confirm the asset exists
    asset_repo.get_by_id(db, asset_id)
    app = asset_app_repo.get_by_id(db, app_id)
    # Confirm the app belongs to this asset
    if app.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Application {app_id} not found under asset {asset_id}")

    old_port = app.port
    old_protocol = app.protocol or "tcp"

    update_data = data.model_dump(exclude_none=True)
    asset_app_repo.update(db, app, **update_data)

    new_port = app.port
    new_protocol = app.protocol or "tcp"

    # Sync port: write/update the new port into asset_ports
    if new_port:
        asset_repo.upsert_port(
            db,
            asset_id=asset_id,
            port_number=new_port,
            protocol=new_protocol,
            service_name=app.name,
            service_version=app.version,
            state="open",
        )
    db.commit()
    return AssetAppRead.model_validate(app)


def delete_app(db: Session, asset_id: int, app_id: int) -> None:
    """Soft delete an application"""
    # Confirm the asset exists
    asset_repo.get_by_id(db, asset_id)
    app = asset_app_repo.get_by_id(db, app_id)
    # Confirm the app belongs to this asset
    if app.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Application {app_id} not found under asset {asset_id}")

    asset_app_repo.soft_delete(db, app)
    db.commit()


def export_apps_csv(db: Session, asset_id: int) -> str:
    """Export an asset's application inventory as CSV"""
    asset = asset_repo.get_by_id(db, asset_id)
    apps = asset_app_repo.list_by_asset(db, asset_id)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "App Name", "Version", "Category", "Port", "Protocol",
        "Install Path", "Config Path", "Notes", "Source", "Status",
        "Created At", "Updated At",
    ])

    for a in apps:
        writer.writerow([
            a.name, a.version or "", a.category or "",
            a.port or "", a.protocol or "",
            a.install_path or "", a.config_path or "",
            a.notes or "", a.source, a.status,
            a.created_at.isoformat(), a.updated_at.isoformat(),
        ])

    return output.getvalue()


def search_apps(db: Session, q: str) -> AppSearchResponse:
    """Global application search"""
    results = asset_app_repo.search_global(db, q)
    items = [AppSearchItem(**r) for r in results]
    return AppSearchResponse(items=items, total=len(items))


def get_app_names(db: Session) -> list[str]:
    """Get all application names (deduplicated, for autocomplete)"""
    return asset_app_repo.get_all_names(db)
