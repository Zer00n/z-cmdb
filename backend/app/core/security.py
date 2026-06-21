"""
Security module: password hashing (argon2id) + JWT encode/decode
"""
import logging
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# argon2id params: m=65536(64MB), t=3, p=4 (per PRD 9.1)
_ph = PasswordHasher(
    memory_cost=65536,
    time_cost=3,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    """Hash a plaintext password with argon2id"""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password, return True/False.
    Does not raise exceptions; the caller decides next steps.
    """
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except (VerificationError, InvalidHashError) as exc:
        logger.warning("password verify error", extra={"error": str(exc)})
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if the hash needs to be upgraded (when parameters change)"""
    return _ph.check_needs_rehash(hashed)


def create_access_token(user_id: int, role: str) -> str:
    """Generate an access_token, valid for JWT_ACCESS_EXPIRE_MINUTES minutes"""
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
    """Generate a refresh_token, valid for JWT_REFRESH_EXPIRE_DAYS days"""
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
    Decode and verify a JWT.
    Raises AuthenticationError on failure.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise AuthenticationError(f"Token invalid or expired: {exc}") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Wrong token type, expected {expected_type}")

    return payload
