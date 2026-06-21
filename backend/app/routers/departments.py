"""
部门管理路由
GET    /api/departments          部门列表
POST   /api/departments          创建部门 (super_admin)
PUT    /api/departments/{id}     更新部门 (super_admin)
DELETE /api/departments/{id}     删除部门 (super_admin)
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
    """部门列表"""
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
    """创建部门"""
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
    """更新部门"""
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
    """删除部门"""
    cost_repo.delete_department(db, dept_id)
    audit_service.log_from_request(
        db, request, action_type="DELETE", user=current_user,
        target_type="department", target_id=str(dept_id),
    )
    db.commit()
    return {"message": "部门已删除"}
