"""
鉴权模块单元测试
覆盖：登录、刷新、修改密码、锁定机制、角色依赖
"""
import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.repositories import user_repo
from app.services import auth_service
from app.core.exceptions import (
    AuthenticationError,
    AccountLockedError,
    ValidationError,
)


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def admin_user(db: Session) -> User:
    """创建一个测试用 admin 用户"""
    pwd_hash = hash_password("Test@1234567")
    user = user_repo.create_user(
        db=db,
        username="testadmin",
        password_hash=pwd_hash,
        role="admin",
        full_name="测试管理员",
    )
    db.commit()
    return user


# ── 密码哈希测试 ──────────────────────────────────────────────


def test_hash_password_and_verify():
    """正确密码应验证通过"""
    plain = "MySecret@2026"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_wrong_password():
    """错误密码应验证失败"""
    hashed = hash_password("Correct@2026")
    assert verify_password("Wrong@2026", hashed) is False


# ── 登录测试 ──────────────────────────────────────────────────


def test_login_success(db: Session, admin_user: User):
    """正确凭据登录成功，返回两个 token"""
    access, refresh = auth_service.login(db, "testadmin", "Test@1234567")
    assert access
    assert refresh


def test_login_wrong_password(db: Session, admin_user: User):
    """错误密码抛 AuthenticationError"""
    with pytest.raises(AuthenticationError):
        auth_service.login(db, "testadmin", "WrongPassword@1")


def test_login_nonexistent_user(db: Session):
    """不存在的用户抛 AuthenticationError"""
    with pytest.raises(AuthenticationError):
        auth_service.login(db, "nobody", "Test@1234567")


def test_login_disabled_user(db: Session, admin_user: User):
    """被禁用的账号抛 AuthenticationError"""
    user_repo.update_user(db, admin_user, status="disabled")
    db.commit()
    with pytest.raises(AuthenticationError, match="禁用"):
        auth_service.login(db, "testadmin", "Test@1234567")


# ── 账号锁定测试 ──────────────────────────────────────────────


def test_account_locked_after_max_attempts(db: Session, admin_user: User):
    """连续 5 次失败后账号锁定"""
    for _ in range(4):
        with pytest.raises(AuthenticationError):
            auth_service.login(db, "testadmin", "WrongPass@1")

    # 第 5 次触发锁定
    with pytest.raises(AccountLockedError):
        auth_service.login(db, "testadmin", "WrongPass@1")


def test_login_resets_failed_count(db: Session, admin_user: User):
    """登录成功后失败计数归零"""
    # 先失败 2 次
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            auth_service.login(db, "testadmin", "WrongPass@1")

    # 正确登录
    auth_service.login(db, "testadmin", "Test@1234567")

    db.refresh(admin_user)
    assert admin_user.failed_login_count == 0


# ── Token 测试 ────────────────────────────────────────────────


def test_refresh_token(db: Session, admin_user: User):
    """refresh_token 可以换取新的 access_token"""
    _, refresh = auth_service.login(db, "testadmin", "Test@1234567")
    new_access = auth_service.refresh_access_token(db, refresh)
    assert new_access


def test_refresh_with_access_token_fails(db: Session, admin_user: User):
    """用 access_token 调用 refresh 接口应失败"""
    access, _ = auth_service.login(db, "testadmin", "Test@1234567")
    with pytest.raises(AuthenticationError):
        auth_service.refresh_access_token(db, access)


# ── 修改密码测试 ──────────────────────────────────────────────


def test_change_password_success(db: Session, admin_user: User):
    """正确旧密码可以修改密码"""
    auth_service.change_password(db, admin_user, "Test@1234567", "NewPass@2026!")
    db.refresh(admin_user)
    assert verify_password("NewPass@2026!", admin_user.password_hash)


def test_change_password_wrong_old(db: Session, admin_user: User):
    """旧密码错误抛 AuthenticationError"""
    with pytest.raises(AuthenticationError):
        auth_service.change_password(db, admin_user, "WrongOld@1", "NewPass@2026!")


def test_change_password_same_as_old(db: Session, admin_user: User):
    """新密码与旧密码相同抛 ValidationError"""
    with pytest.raises(ValidationError):
        auth_service.change_password(db, admin_user, "Test@1234567", "Test@1234567")


# ── HTTP 接口测试 ─────────────────────────────────────────────


def test_login_api(client, db_from_client):
    """POST /api/auth/login 返回 access_token"""
    # 先创建用户
    pwd_hash = hash_password("ApiTest@2026")
    user_repo.create_user(db_from_client, "apiuser", pwd_hash, "admin")
    db_from_client.commit()

    resp = client.post("/api/auth/login", json={"username": "apiuser", "password": "ApiTest@2026"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_api_wrong_credentials(client):
    """错误凭据返回 401"""
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "Wrong@1234"})
    assert resp.status_code == 401


def test_change_password_api_requires_auth(client):
    """未认证调用 change-password 返回 401"""
    resp = client.post(
        "/api/auth/change-password",
        json={"old_password": "old", "new_password": "NewPass@2026!"},
    )
    assert resp.status_code == 401


# ── 初始 admin 创建测试 ───────────────────────────────────────


def test_ensure_initial_admin_creates_user(db: Session):
    """空数据库时 ensure_initial_admin 应创建 admin 用户"""
    assert user_repo.count_users(db) == 0
    auth_service.ensure_initial_admin(db)
    assert user_repo.count_users(db) == 1
    user = user_repo.get_by_username(db, "admin")
    assert user is not None
    assert user.role == "super_admin"


def test_ensure_initial_admin_idempotent(db: Session):
    """已有用户时不重复创建"""
    auth_service.ensure_initial_admin(db)
    auth_service.ensure_initial_admin(db)
    assert user_repo.count_users(db) == 1
