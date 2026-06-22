"""
Authentication business logic
Login, token refresh, password change
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
from app.services.config_service import get_session_timeout_minutes

logger = logging.getLogger(__name__)

# Lock account for 15 minutes after 5 failed login attempts
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15


def login(db: Session, username: str, password: str) -> tuple[str, str]:
    """
    Login authentication.
    Returns (access_token, refresh_token).
    Raises AuthenticationError or AccountLockedError on failure.
    """
    user = user_repo.get_by_username(db, username)

    if user is None:
        # Do not reveal whether the user exists; return a generic auth failure
        raise AuthenticationError("Invalid username or password")

    if user.status == "disabled":
        raise AuthenticationError("Account has been disabled")

    # Check lock status
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise AccountLockedError(f"Account locked, please try again in {remaining} minutes")

    # Verify password
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
            raise AccountLockedError(f"Account locked for {LOCK_DURATION_MINUTES} minutes after {MAX_FAILED_ATTEMPTS} consecutive failed login attempts")

        db.commit()
        raise AuthenticationError("Invalid username or password")

    # Login succeeded, reset failed attempt counter
    user_repo.reset_failed_login(db, user)
    db.commit()

    timeout = get_session_timeout_minutes(db)
    access_token = create_access_token(user.id, user.role, expire_minutes=timeout)
    refresh_token = create_refresh_token(user.id, user.role)

    logger.info("user login success", extra={"user_id": user.id, "username": username})
    return access_token, refresh_token


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """
    Exchange a refresh_token for a new access_token.
    Raises AuthenticationError on failure.
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = int(payload["sub"])

    user = user_repo.get_by_id(db, user_id)
    if user.status == "disabled":
        raise AuthenticationError("Account has been disabled")

    timeout = get_session_timeout_minutes(db)
    return create_access_token(user.id, user.role, expire_minutes=timeout)


def change_password(
    db: Session, user: User, old_password: str, new_password: str
) -> None:
    """
    Change password: verify old password then update.
    Raises AuthenticationError or ValidationError on failure.
    """
    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError("Incorrect old password")

    if old_password == new_password:
        raise ValidationError("New password cannot be the same as the old password")

    new_hash = hash_password(new_password)
    user_repo.update_password(db, user, new_hash)
    db.commit()

    logger.info("password changed", extra={"user_id": user.id})


def generate_initial_password() -> str:
    """Generate a random initial password that meets the password policy"""
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
    """Check whether the password meets the minimum policy: >=8 chars, upper/lower/digit/symbol"""
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    return has_upper and has_lower and has_digit and has_symbol


def _persist_initial_password(password: str) -> None:
    """
    Write the initial password to INITIAL_ADMIN_PASSWORD.txt in the data directory.
    Permissions 600 (owner read/write only); also prints to stdout.
    """
    from app.core.config import settings

    pw_file = settings.db_path.parent / "INITIAL_ADMIN_PASSWORD.txt"
    pw_file.parent.mkdir(parents=True, exist_ok=True)
    pw_file.write_text(password, encoding="utf-8")
    # chmod is not supported on Windows; set permissions only on POSIX systems
    try:
        pw_file.chmod(0o600)
    except OSError:
        pass

    print(f"\n{'='*60}")
    print(f"  Initial admin password saved to: {pw_file}")
    print(f"  Username: admin")
    print(f"  Password: {password}")
    print(f"  Please change your password immediately after logging in!")
    print(f"{'='*60}\n")


def ensure_initial_admin(db: Session) -> None:
    """
    On first startup, if the users table is empty, automatically create a super_admin account.
    Prefers the environment variable CMDB_INITIAL_ADMIN_PASSWORD (must meet password policy);
    otherwise generates a random password. The effective password is written to
    data/INITIAL_ADMIN_PASSWORD.txt.
    """
    from app.core.config import settings

    if user_repo.count_users(db) > 0:
        return

    # Prefer environment variable
    initial_password = ""
    env_password = settings.INITIAL_ADMIN_PASSWORD
    if env_password:
        if _check_password_policy(env_password):
            initial_password = env_password
            logger.info("using INITIAL_ADMIN_PASSWORD from environment")
        else:
            logger.warning(
                "CMDB_INITIAL_ADMIN_PASSWORD does not meet password policy (>=8 chars, "
                "upper/lower/digit/symbol), falling back to random generation"
            )

    if not initial_password:
        initial_password = generate_initial_password()

    password_hash = hash_password(initial_password)

    user_repo.create_user(
        db=db,
        username="admin",
        password_hash=password_hash,
        role="super_admin",
        full_name="System Administrator",
    )
    db.commit()

    _persist_initial_password(initial_password)
