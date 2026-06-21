"""
Department management routes
GET    /api/departments          Department list
POST   /api/departments          Create department (super_admin)
PUT    /api/departments/{id}     Update department (super_admin)
DELETE /api/departments/{id}     Delete department (super_admin)
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, SuperAdminUser
from app.repositories import cost_repo
from app.services import audit_service

router = APIRouter(prefix="/api/departments", tags=["departments"])


class DepartmentCreate(BaseModel):
    name: str
    code: str


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None


@router.get("")
def list_departments(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Department list"""
    depts = cost_repo.get_departments(db)
    return [
        {"id": d.id, "name": d.name, "code": d.code}
        for d in depts
    ]


@router.post("")
def create_department(
    body: DepartmentCreate,
    request: Request,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Create department"""
    dept = cost_repo.create_department(db, name=body.name, code=body.code)
    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,
        target_type="department", target_id=str(dept.id),
        details={"name": dept.name, "code": dept.code},
    )
    db.commit()
    return {"id": dept.id, "name": dept.name, "code": dept.code}


@router.put("/{dept_id}")
def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    request: Request,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Update department"""
    dept = cost_repo.update_department(
        db, dept_id,
        name=body.name,
        code=body.code,
    )
    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="department", target_id=str(dept.id),
    )
    db.commit()
    return {"id": dept.id, "name": dept.name, "code": dept.code}


@router.delete("/{dept_id}")
def delete_department(
    dept_id: int,
    request: Request,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Delete department"""
    cost_repo.delete_department(db, dept_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=current_user,
        target_type="department", target_id=str(dept_id),
    )
    db.commit()
    return {"message": "Department deleted"}
