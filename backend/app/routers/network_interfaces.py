"""
Network interface API (P0)
GET    /api/assets/{id}/interfaces               List interfaces
POST   /api/assets/{id}/interfaces               Create interface
PATCH  /api/assets/{id}/interfaces/{iface_id}    Update interface
DELETE /api/assets/{id}/interfaces/{iface_id}    Delete interface
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.schemas.asset import (
    NetworkInterfaceCreate, NetworkInterfaceRead,
)
from app.services import audit_service, network_interface_service

router = APIRouter(tags=["network-interfaces"])


@router.get(
    "/api/assets/{asset_id}/interfaces",
    response_model=list[NetworkInterfaceRead],
)
def list_interfaces(
    asset_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
):
    return network_interface_service.list_interfaces(db, asset_id)


@router.get(
    "/api/assets/{asset_id}/interfaces/{interface_id}",
    response_model=NetworkInterfaceRead,
)
def get_interface(
    asset_id: int,
    interface_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
):
    return network_interface_service.get_interface(db, asset_id, interface_id)


@router.post(
    "/api/assets/{asset_id}/interfaces",
    response_model=NetworkInterfaceRead,
    status_code=201,
)
def create_interface(
    asset_id: int,
    body: NetworkInterfaceCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    interface = network_interface_service.create_interface(db, asset_id, body)
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,
        target_type="network_interface", target_id=str(interface.id),
        details=body.model_dump(exclude_none=True),
    )
    db.commit()
    return interface


@router.patch(
    "/api/assets/{asset_id}/interfaces/{interface_id}",
    response_model=NetworkInterfaceRead,
)
def update_interface(
    asset_id: int,
    interface_id: int,
    body: NetworkInterfaceCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    interface = network_interface_service.update_interface(
        db, asset_id, interface_id, body
    )
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="network_interface", target_id=str(interface_id),
        details=body.model_dump(exclude_none=True),
    )
    db.commit()
    return interface


@router.delete(
    "/api/assets/{asset_id}/interfaces/{interface_id}",
    status_code=204,
)
def delete_interface(
    asset_id: int,
    interface_id: int,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    network_interface_service.delete_interface(db, asset_id, interface_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=current_user,
        target_type="network_interface", target_id=str(interface_id),
    )
    db.commit()
