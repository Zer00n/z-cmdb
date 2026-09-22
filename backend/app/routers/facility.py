"""
Facility API: datacenter / rack views and rack CRUD.
GET  /api/facility/datacenters                    Datacenter summary list
GET  /api/facility/datacenters/{name}/racks       Racks + unlocated in a datacenter
GET  /api/facility/racks/{id}/elevation           Rack elevation (devices + links + warnings)
POST /api/facility/racks                          Add an empty rack (admin)
PATCH /api/facility/racks/{id}                    Edit rack metadata (admin)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.schemas.facility import (
    DatacenterRacks,
    DatacenterSummary,
    RackCreate,
    RackElevation,
    RackRead,
    RackUpdate,
)
from app.services import audit_service, facility_service

router = APIRouter(prefix="/api/facility", tags=["facility"])


@router.get("/datacenters", response_model=list[DatacenterSummary])
def list_datacenters(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
):
    return facility_service.list_datacenters(db)


@router.get(
    "/datacenters/{datacenter}/racks",
    response_model=DatacenterRacks,
)
def list_datacenter_racks(
    datacenter: str,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
):
    return facility_service.list_datacenter_racks(db, datacenter)


@router.get("/racks/{rack_id}/elevation", response_model=RackElevation)
def get_rack_elevation(
    rack_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
):
    return facility_service.get_rack_elevation(db, rack_id)


@router.post("/racks", response_model=RackRead, status_code=201)
def create_rack(
    body: RackCreate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    rack = facility_service.create_rack(db, body)
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,
        target_type="rack", target_id=str(rack.id),
        details={"datacenter": rack.datacenter, "name": rack.name},
    )
    db.commit()
    return rack


@router.patch("/racks/{rack_id}", response_model=RackRead)
def update_rack(
    rack_id: int,
    body: RackUpdate,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
):
    rack = facility_service.update_rack(db, rack_id, body)
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="rack", target_id=str(rack.id),
        details=body.model_dump(exclude_none=True),
    )
    db.commit()
    return rack
