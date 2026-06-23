"""
Asset data access layer
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AssetNotFoundError, DuplicateError
from app.models.asset import Asset, AssetPort
from app.schemas.asset import AssetQueryParams

logger = logging.getLogger(__name__)


def get_by_id(db: Session, asset_id: int, load_ports: bool = False) -> Asset:
    if load_ports:
        stmt = (
            select(Asset)
            .options(selectinload(Asset.ports))
            .where(Asset.id == asset_id)
        )
        asset = db.scalar(stmt)
    else:
        asset = db.get(Asset, asset_id)
    if asset is None:
        raise AssetNotFoundError(f"Asset ID {asset_id} not found")
    return asset


def get_by_asset_no(db: Session, asset_no: str) -> Asset | None:
    return db.scalar(select(Asset).where(Asset.asset_no == asset_no))


def get_by_ip(db: Session, ip_address: str) -> Asset | None:
    return db.scalar(select(Asset).where(Asset.ip_address == ip_address))


def get_by_mac(db: Session, mac_address: str) -> Asset | None:
    if not mac_address:
        return None
    return db.scalar(select(Asset).where(Asset.mac_address == mac_address))


def list_assets(db: Session, params: AssetQueryParams) -> tuple[list[Asset], int]:
    """Return (asset list, total count)"""
    stmt = select(Asset)
    count_stmt = select(func.count()).select_from(Asset)

    # Filter conditions
    filters = []
    if params.search:
        kw = f"%{params.search}%"
        # v2.5: search scope extended to business_system + app name/version
        from sqlalchemy import exists
        from app.models.asset_app import AssetApp

        asset_match = or_(
            Asset.ip_address.like(kw),
            Asset.hostname.like(kw),
            Asset.asset_no.like(kw),
            Asset.remark.like(kw),
            Asset.owner.like(kw),
            Asset.business_system.like(kw),  # v2.5 addition
        )

        app_match = exists().where(
            AssetApp.asset_id == Asset.id,
            AssetApp.status == "active",
            or_(
                AssetApp.name.like(kw),
                AssetApp.version.like(kw),
            ),
        )

        filters.append(or_(asset_match, app_match))
    if params.asset_type:
        filters.append(Asset.asset_type == params.asset_type)
    if params.network_zone:
        filters.append(Asset.network_zone == params.network_zone)
    if params.importance:
        filters.append(Asset.importance == params.importance)
    if params.status:
        filters.append(Asset.status == params.status)
    if params.business_system:
        filters.append(Asset.business_system == params.business_system)
    if params.owner:
        filters.append(Asset.owner == params.owner)
    if params.source:
        filters.append(Asset.source == params.source)

    if filters:
        from sqlalchemy import and_
        stmt = stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    # Sort by: asset_no
    stmt = stmt.order_by(Asset.asset_no)

    # Total count
    total = db.scalar(count_stmt) or 0

    # Pagination
    offset = (params.page - 1) * params.page_size
    stmt = stmt.offset(offset).limit(params.page_size)

    assets = list(db.scalars(stmt).all())
    return assets, total


def generate_asset_no(db: Session) -> str:
    """Generate asset number: {prefix}-YYYYMMDD-NNN, prefix read from system config"""
    from datetime import date

    from app.services.config_service import get_asset_no_prefix
    prefix = get_asset_no_prefix(db)
    today = date.today().strftime("%Y%m%d")
    full_prefix = f"{prefix}-{today}-"

    # Find today's highest sequence number
    stmt = (
        select(Asset.asset_no)
        .where(Asset.asset_no.like(f"{full_prefix}%"))
        .order_by(Asset.asset_no.desc())
        .limit(1)
    )
    last = db.scalar(stmt)
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{full_prefix}{seq:03d}"


def create_asset(db: Session, **kwargs) -> Asset:  # type: ignore[type-arg]
    asset_no = kwargs.get("asset_no")
    if asset_no and get_by_asset_no(db, asset_no):
        raise DuplicateError(f"Asset number {asset_no} already exists")

    if not asset_no:
        kwargs["asset_no"] = generate_asset_no(db)

    asset = Asset(**kwargs)
    db.add(asset)
    db.flush()
    logger.info("asset created", extra={"asset_id": asset.id, "asset_no": asset.asset_no})
    return asset


def update_asset(db: Session, asset: Asset, **kwargs) -> Asset:  # type: ignore[type-arg]
    for key, value in kwargs.items():
        if hasattr(asset, key) and value is not None:
            setattr(asset, key, value)
    asset.updated_at = datetime.now(timezone.utc)
    db.flush()
    return asset


def decommission_asset(db: Session, asset: Asset) -> Asset:
    """Soft delete: mark as decommissioned"""
    asset.status = "decommissioned"
    asset.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("asset decommissioned", extra={"asset_id": asset.id})
    return asset


# ── Port operations ──────────────────────────────────────────────

def upsert_port(
    db: Session,
    asset_id: int,
    port_number: int,
    protocol: str,
    service_name: str | None = None,
    service_version: str | None = None,
    state: str | None = "open",
) -> AssetPort:
    """Insert or update a port record"""
    stmt = select(AssetPort).where(
        AssetPort.asset_id == asset_id,
        AssetPort.port_number == port_number,
        AssetPort.protocol == protocol,
    )
    port = db.scalar(stmt)
    if port is None:
        port = AssetPort(
            asset_id=asset_id,
            port_number=port_number,
            protocol=protocol,
        )
        db.add(port)

    port.service_name = service_name
    port.service_version = service_version
    port.state = state
    port.last_seen_at = datetime.now(timezone.utc)
    db.flush()
    return port


def get_ports_by_asset(db: Session, asset_id: int) -> list[AssetPort]:
    stmt = select(AssetPort).where(AssetPort.asset_id == asset_id).order_by(AssetPort.port_number)
    return list(db.scalars(stmt).all())
