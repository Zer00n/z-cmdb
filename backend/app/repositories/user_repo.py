"""
用户数据访问层
所有数据库操作集中在此，Service 层不直接操作 ORM
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, UserNotFoundError
from app.models.user import User

logger = logging.getLogger(__name__)


def get_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"用户 ID {user_id} 不存在")
    return user


def get_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return db.scalar(stmt)


def get_by_username_or_raise(db: Session, username: str) -> User:
    user = get_by_username(db, username)
    if user is None:
        raise UserNotFoundError(f"用户 {username} 不存在")
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    stmt = select(User).offset(skip).limit(limit).order_by(User.created_at)
    return list(db.scalars(stmt).all())


def count_users(db: Session) -> int:
    from sqlalchemy import func
    return db.scalar(select(func.count()).select_from(User)) or 0


def create_user(
    db: Session,
    username: str,
    password_hash: str,
    role: str,
    full_name: str | None = None,
    email: str | None = None,
) -> User:
    # 检查用户名唯一性
    if get_by_username(db, username) is not None:
        raise DuplicateError(f"用户名 {username} 已存在")

    user = User(
        username=username,
        password_hash=password_hash,
        role=role,
        full_name=full_name,
        email=email,
        status="active",
        failed_login_count=0,
    )
    db.add(user)
    db.flush()  # 获取 id，不 commit（由 Service 层控制事务）
    logger.info("user created", extra={"user_id": user.id, "username": username, "role": role})
    return user


def update_user(db: Session, user: User, **kwargs) -> User:  # type: ignore[type-arg]
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    return user


def increment_failed_login(db: Session, user: User) -> User:
    user.failed_login_count = (user.failed_login_count or 0) + 1
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    return user


def reset_failed_login(db: Session, user: User) -> User:
    user.failed_login_count = 0
    user.locked_until = None
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    return user


def lock_user(db: Session, user: User, until: datetime) -> User:
    user.locked_until = until
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    return user


def update_password(db: Session, user: User, new_hash: str) -> User:
    user.password_hash = new_hash
    user.password_changed_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    return user
