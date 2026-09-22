"""
Network interface data access layer (P0)
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.asset import NetworkInterface

logger = logging.getLogger(__name__)


def list_for_asset(db: Session, asset_id: int) -> list[NetworkInterface]:
    stmt = (
        select(NetworkInterface)
        .where(NetworkInterface.asset_id == asset_id)
        .order_by(
            NetworkInterface.is_primary.desc(),
            NetworkInterface.name,
            NetworkInterface.ip_address,
        )
    )
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, interface_id: int) -> NetworkInterface:
    interface = db.get(NetworkInterface, interface_id)
    if interface is None:
        raise NotFoundError(f"Network interface {interface_id} not found")
    return interface


def create_interface(db: Session, asset_id: int, **kwargs) -> NetworkInterface:
    interface = NetworkInterface(asset_id=asset_id, **kwargs)
    db.add(interface)
    db.flush()
    # Enforce a single primary interface per asset
    if interface.is_primary:
        _clear_other_primary(db, asset_id, interface.id)
    logger.info(
        "network interface created",
        extra={"asset_id": asset_id, "interface_id": interface.id},
    )
    return interface


def update_interface(db: Session, interface: NetworkInterface, **kwargs) -> NetworkInterface:
    for key, value in kwargs.items():
        if hasattr(interface, key) and value is not None:
            setattr(interface, key, value)
    interface.updated_at = datetime.now(timezone.utc)
    db.flush()
    if interface.is_primary:
        _clear_other_primary(db, interface.asset_id, interface.id)
    return interface


def delete_interface(db: Session, interface: NetworkInterface) -> None:
    db.delete(interface)
    db.flush()


def _clear_other_primary(db: Session, asset_id: int, keep_id: int) -> None:
    """Ensure at most one primary interface per asset."""
    rows = db.scalars(
        select(NetworkInterface).where(
            NetworkInterface.asset_id == asset_id,
            NetworkInterface.id != keep_id,
            NetworkInterface.is_primary.is_(True),
        )
    ).all()
    for row in rows:
        row.is_primary = False
