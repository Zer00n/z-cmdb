"""
User management routes (super_admin only)
GET    /api/users
POST   /api/users
GET    /api/users/{id}
PATCH  /api/users/{id}
DELETE /api/users/{id}    Soft delete (status=disabled)
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import SuperAdminUser
from app.core.security import hash_password
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> list[UserRead]:
    """User list (super_admin only)"""
    users = user_repo.list_users(db)
    return users  # type: ignore[return-value]


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    body: UserCreate,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> UserRead:
    """Create user (super_admin only)"""
    pwd_hash = hash_password(body.password)
    user = user_repo.create_user(
        db=db,
        username=body.username,
        password_hash=pwd_hash,
        role=body.role,
        full_name=body.full_name,
        email=body.email,
    )
    audit_service.log_action(
        db, action_type="CREATE", user=current_user,  # type: ignore[arg-type]
        target_type="user", target_id=user.id,
        details={"username": user.username, "role": user.role},
    )
    db.commit()
    return user  # type: ignore[return-value]


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> UserRead:
    """User detail (super_admin only)"""
    return user_repo.get_by_id(db, user_id)  # type: ignore[return-value]


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> UserRead:
    """Update user (super_admin only)"""
    user = user_repo.get_by_id(db, user_id)
    update_data = body.model_dump(exclude_none=True)
    user_repo.update_user(db, user, **update_data)
    audit_service.log_action(
        db, action_type="UPDATE", user=current_user,  # type: ignore[arg-type]
        target_type="user", target_id=user.id,
        details=update_data,
    )
    db.commit()
    return user  # type: ignore[return-value]


@router.delete("/{user_id}", status_code=204)
def disable_user(
    user_id: int,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> None:
    """Disable user (soft delete, super_admin only)"""
    user = user_repo.get_by_id(db, user_id)
    user.token_version = (user.token_version or 0) + 1
    user_repo.update_user(db, user, status="disabled")
    audit_service.log_action(
        db, action_type="DELETE", user=current_user,  # type: ignore[arg-type]
        target_type="user", target_id=user.id,
        details={"action": "disabled"},
    )
    db.commit()
