"""
Network interface business logic (P0)
"""
import logging

from sqlalchemy.orm import Session

from app.repositories import asset_repo, network_interface_repo
from app.schemas.asset import NetworkInterfaceCreate

logger = logging.getLogger(__name__)


def list_interfaces(db: Session, asset_id: int):
    asset_repo.get_by_id(db, asset_id)  # 404 if asset missing
    return network_interface_repo.list_for_asset(db, asset_id)


def get_interface(db: Session, asset_id: int, interface_id: int):
    interface = network_interface_repo.get_by_id(db, interface_id)
    if interface.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Network interface {interface_id} not found")
    return interface


def create_interface(db: Session, asset_id: int, data: NetworkInterfaceCreate):
    asset_repo.get_by_id(db, asset_id)
    payload = data.model_dump(exclude_none=True)
    interface = network_interface_repo.create_interface(db, asset_id, **payload)
    return interface


def update_interface(db: Session, asset_id: int, interface_id: int, data):
    interface = network_interface_repo.get_by_id(db, interface_id)
    if interface.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Network interface {interface_id} not found")
    payload = data.model_dump(exclude_none=True)
    return network_interface_repo.update_interface(db, interface, **payload)


def delete_interface(db: Session, asset_id: int, interface_id: int) -> None:
    interface = network_interface_repo.get_by_id(db, interface_id)
    if interface.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Network interface {interface_id} not found")
    network_interface_repo.delete_interface(db, interface)
