"""
安全模块：密码哈希（argon2id）+ JWT 编解码
"""
import logging
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# argon2id 参数：m=65536(64MB), t=3, p=4（符合 PRD 9.1）
_ph = PasswordHasher(
    memory_cost=65536,
    time_cost=3,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    """对明文密码进行 argon2id 哈希"""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    验证密码，返回 True/False。
    不抛异常，由调用方决定后续逻辑。
    """
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except (VerificationError, InvalidHashError) as exc:
        logger.warning("password verify error", extra={"error": str(exc)})
        return False


def needs_rehash(hashed: str) -> bool:
    """检查哈希是否需要升级（参数变更时）"""
    return _ph.check_needs_rehash(hashed)


def create_access_token(user_id: int, role: str) -> str:
    """生成 access_token，有效期 JWT_ACCESS_EXPIRE_MINUTES 分钟"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int, role: str) -> str:
    """生成 refresh_token，有效期 JWT_REFRESH_EXPIRE_DAYS 天"""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    解码并验证 JWT。
    失败时抛 AuthenticationError。
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise AuthenticationError(f"Token 无效或已过期: {exc}") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Token 类型错误，期望 {expected_type}")

    return payload
