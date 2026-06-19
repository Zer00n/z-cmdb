"""
鉴权业务逻辑
登录、刷新 Token、修改密码
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories import user_repo

logger = logging.getLogger(__name__)

# 5 次失败登录后锁定 15 分钟
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15


def login(db: Session, username: str, password: str) -> tuple[str, str]:
    """
    登录验证。
    返回 (access_token, refresh_token)。
    失败时抛 AuthenticationError 或 AccountLockedError。
    """
    user = user_repo.get_by_username(db, username)

    if user is None:
        # 不暴露"用户不存在"，统一返回认证失败
        raise AuthenticationError("用户名或密码错误")

    if user.status == "disabled":
        raise AuthenticationError("账号已被禁用")

    # 检查锁定状态
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise AccountLockedError(f"账号已锁定，请 {remaining} 分钟后重试")

    # 验证密码
    if not verify_password(password, user.password_hash):
        user = user_repo.increment_failed_login(db, user)

        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_DURATION_MINUTES)
            user_repo.lock_user(db, user, lock_until)
            db.commit()
            logger.warning(
                "account locked due to failed attempts",
                extra={"user_id": user.id, "username": username},
            )
            raise AccountLockedError(f"连续登录失败 {MAX_FAILED_ATTEMPTS} 次，账号已锁定 {LOCK_DURATION_MINUTES} 分钟")

        db.commit()
        raise AuthenticationError("用户名或密码错误")

    # 登录成功，重置失败计数
    user_repo.reset_failed_login(db, user)
    db.commit()

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    logger.info("user login success", extra={"user_id": user.id, "username": username})
    return access_token, refresh_token


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """
    用 refresh_token 换新的 access_token。
    失败时抛 AuthenticationError。
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = int(payload["sub"])

    user = user_repo.get_by_id(db, user_id)
    if user.status == "disabled":
        raise AuthenticationError("账号已被禁用")

    return create_access_token(user.id, user.role)


def change_password(
    db: Session, user: User, old_password: str, new_password: str
) -> None:
    """
    修改密码：验证旧密码后更新。
    失败时抛 AuthenticationError 或 ValidationError。
    """
    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError("旧密码错误")

    if old_password == new_password:
        raise ValidationError("新密码不能与旧密码相同")

    new_hash = hash_password(new_password)
    user_repo.update_password(db, user, new_hash)
    db.commit()

    logger.info("password changed", extra={"user_id": user.id})


def generate_initial_password() -> str:
    """生成符合密码策略的随机初始密码"""
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(16))
        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_symbol = any(not c.isalnum() for c in pwd)
        if has_upper and has_lower and has_digit and has_symbol:
            return pwd


def _check_password_policy(password: str) -> bool:
    """检查密码是否满足最低策略：>=8 位，含大小写、数字、符号"""
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    return has_upper and has_lower and has_digit and has_symbol


def _persist_initial_password(password: str) -> None:
    """
    将初始密码写入 data 目录下的 INITIAL_ADMIN_PASSWORD.txt。
    权限 600（仅文件属主可读写），同时打印到 stdout。
    """
    from app.core.config import settings

    pw_file = settings.db_path.parent / "INITIAL_ADMIN_PASSWORD.txt"
    pw_file.parent.mkdir(parents=True, exist_ok=True)
    pw_file.write_text(password, encoding="utf-8")
    # Windows 不支持 chmod，仅在 POSIX 系统上设置权限
    try:
        pw_file.chmod(0o600)
    except OSError:
        pass

    print(f"\n{'='*60}")
    print(f"  初始管理员密码已保存至：{pw_file}")
    print(f"  用户名: admin")
    print(f"  密  码: {password}")
    print(f"  请登录后立即修改密码！")
    print(f"{'='*60}\n")


def ensure_initial_admin(db: Session) -> None:
    """
    首次启动时，若 users 表为空，自动创建 super_admin 账号。
    优先使用环境变量 CMDB_INITIAL_ADMIN_PASSWORD（需满足密码策略），
    否则随机生成。生效的密码写入 data/INITIAL_ADMIN_PASSWORD.txt。
    """
    from app.core.config import settings

    if user_repo.count_users(db) > 0:
        return

    # 优先读环境变量
    initial_password = ""
    env_password = settings.INITIAL_ADMIN_PASSWORD
    if env_password:
        if _check_password_policy(env_password):
            initial_password = env_password
            logger.info("using INITIAL_ADMIN_PASSWORD from environment")
        else:
            logger.warning(
                "CMDB_INITIAL_ADMIN_PASSWORD 不满足密码策略（>=8位，含大小写/数字/符号），"
                "回退到随机生成"
            )

    if not initial_password:
        initial_password = generate_initial_password()

    password_hash = hash_password(initial_password)

    user_repo.create_user(
        db=db,
        username="admin",
        password_hash=password_hash,
        role="super_admin",
        full_name="系统管理员",
    )
    db.commit()

    _persist_initial_password(initial_password)
