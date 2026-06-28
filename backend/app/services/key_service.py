"""
SQLite 静态加密 — 生命周期编排服务

PRD §4（状态机与解锁流程）+ §5（生命周期流程）+ 操作指南任务 5 的实现入口。

职责：
  - setup：首次初始化（无 keystore）→ 生成 DEK + 入册初始 admin + 恢复码 + 开库迁移
  - unlock：口令或恢复码解开 DEK → init_engine → 首次迁移 → （口令）签发 JWT → UNLOCKED
  - change_password_and_rewrap：改密时库内哈希与 keystore 记录原子同步（PRD §5.3）
  - register_admin / unregister_admin：增删管理员入册（PRD §5.4）
  - 防爆破：失败计数落盘、指数退避、阈值锁定、统一错误（PRD §4.2）

密钥材料绝不进日志（操作指南 §0.1）。
"""
from __future__ import annotations

import json
import logging
import secrets
import string
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from sqlalchemy.orm import Session

from app.core import crypto, database, keyvault
from app.core.config import settings
from app.core.exceptions import (
    LockStateError,
    UnlockError,
    UnlockLockedOutError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories import user_repo
from app.services.config_service import get_session_timeout_minutes

logger = logging.getLogger(__name__)

# ── 防爆破参数 ────────────────────────────────────────────────────────────────
MAX_UNLOCK_ATTEMPTS = 5
BASE_LOCK_SECONDS = 60          # 首次锁定时长
LOCK_CAP_SECONDS = 3600         # 单次锁定上限（1 小时）


def keystore_path() -> Path:
    """keystore.json 与加密库同目录（data/）。"""
    return settings.db_path.parent / "keystore.json"


def _attempts_path() -> Path:
    """失败计数落盘文件（PRD §4.2：不进内存，防重启清零绕过）。"""
    return settings.db_path.parent / ".unlock_attempts"


# ── 初始口令生成 / 持久化（内联，避免 key_service→auth_service 依赖）────────


def generate_initial_password() -> str:
    """生成满足密码策略（大小写+数字+特殊、16 位）的随机口令。"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(16))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(not c.isalnum() for c in pwd)
        ):
            return pwd


def _persist_initial_password(password: str, username: str) -> None:
    """系统随机生成口令时，一次性落盘 + 控制台提示（改密后由 auth 清除）。"""
    pw_file = settings.db_path.parent / "INITIAL_ADMIN_PASSWORD.txt"
    pw_file.parent.mkdir(parents=True, exist_ok=True)
    pw_file.write_text(password, encoding="utf-8")
    try:
        pw_file.chmod(0o600)
    except OSError:
        pass
    print(f"\n{'='*60}\n  Initial admin password saved to: {pw_file}\n"
          f"  Username: {username}\n  Password: {password}\n"
          f"  Change it immediately after first login!\n{'='*60}\n")


def needs_setup() -> bool:
    """是否处于首次初始化状态（keystore 不存在）。"""
    return not crypto.keystore_exists(keystore_path())


# ── 防爆破 ────────────────────────────────────────────────────────────────────


def _read_attempts() -> dict:
    p = _attempts_path()
    if not p.exists():
        return {"count": 0, "first_failed_at": 0, "lock_series": 0, "locked_until": 0}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 损坏则重置
        return {"count": 0, "first_failed_at": 0, "lock_series": 0, "locked_until": 0}


def _write_attempts(data: dict) -> None:
    p = _attempts_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    import os
    os.replace(tmp, p)
    try:
        p.chmod(0o600)
    except OSError:
        pass


def _check_rate_limit() -> None:
    """解锁前检查是否处于锁定窗口；是则抛 UnlockLockedOutError。"""
    data = _read_attempts()
    locked_until = data.get("locked_until", 0)
    if locked_until and time.time() < locked_until:
        remaining = int(locked_until - time.time())
        raise UnlockLockedOutError(retry_after_seconds=remaining)


def _record_failure() -> None:
    data = _read_attempts()
    now = int(time.time())
    data["count"] = data.get("count", 0) + 1
    if data.get("first_failed_at", 0) == 0:
        data["first_failed_at"] = now
    if data["count"] >= MAX_UNLOCK_ATTEMPTS:
        # 指数退避：第 N 次进锁，时长 = BASE << (lock_series)，封顶 LOCK_CAP
        series = data.get("lock_series", 0)
        delay = min(LOCK_CAP_SECONDS, BASE_LOCK_SECONDS << series)
        data["locked_until"] = now + delay
        data["lock_series"] = series + 1
        data["count"] = 0  # 进入新锁定窗口，计数重置
        logger.warning("unlock locked out due to repeated failures (series=%d)", series + 1)
    _write_attempts(data)


def _reset_attempts() -> None:
    p = _attempts_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


# ── 迁移（解锁/setup 之后执行，PRD §6）────────────────────────────────────────


def run_migrations() -> None:
    """在已 key 的引擎上执行 alembic upgrade head。

    env.py 从 keyvault 取 DEK / 复用 database.get_engine()，故此处只需驱动
    alembic command。迁移幂等：已是最新的 revision 时无操作。
    """
    from alembic.config import Config
    from alembic import command

    backend_root = Path(__file__).resolve().parent.parent.parent  # backend/
    cfg = Config()
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.config_file_name = str(backend_root / "alembic.ini")
    command.upgrade(cfg, "head")
    keyvault.mark_migrated()


# ── setup（首次初始化，PRD §5.1）──────────────────────────────────────────────


@dataclass
class SetupResult:
    recovery_code: str          # 一次性恢复码（展示串，含连字符）
    admin_username: str
    admin_password: str | None  # 仅系统随机生成时非空；用户自设时为 None
    message: str


def setup(admin_username: str = "admin", admin_password: str | None = None) -> SetupResult:
    """首次初始化。仅当 needs_setup() 时可用。

    流程：生成 DEK + 恢复码 → 落 keystore（密钥材料持久化）→ init_engine +
    迁移 + 建库内 admin → UNLOCKED。任一步失败则回滚 keystore 以保持状态干净。
    """
    if not needs_setup():
        raise LockStateError("Keystore already exists; use unlock instead")
    if not admin_username:
        raise ValidationError("Admin username is required")

    generated_pw: str | None = None
    if not admin_password:
        admin_password = generate_initial_password()
        generated_pw = admin_password

    # 1) 生成密钥材料
    dek = crypto.new_dek()
    dek_hex = dek.hex()
    recovery_display, recovery_secret = crypto.generate_recovery_code()

    # 2) 先落 keystore（持久化密钥材料；此时库尚未建）
    ks = crypto.Keystore()
    ks.upsert(crypto.build_user_record(dek, admin_username, admin_password))
    ks.upsert(crypto.build_recovery_record(dek, recovery_secret))
    crypto.save_keystore(keystore_path(), ks)
    crypto.secure_wipe(dek)

    # 3) 开加密库 + 迁移 + 建 admin；失败则回滚 keystore
    try:
        database.init_engine(dek_hex)
        if not keyvault.has_migrated():
            run_migrations()
        with database.SessionLocal() as db:  # type: ignore[misc]
            user_repo.create_user(
                db=db,
                username=admin_username,
                password_hash=hash_password(admin_password),
                role="super_admin",
                full_name="System Administrator",
            )
            db.commit()
    except Exception:
        # 回滚：删除 keystore，回到 needs_setup 干净态
        _safe_remove(keystore_path())
        database.shutdown_engine()
        logger.error("setup failed after keystore write; rolled back keystore", exc_info=True)
        raise

    # 4) 切 UNLOCKED，清防爆破计数
    keyvault.unlock_with_dek(dek_hex)
    _reset_attempts()

    # 系统随机生成的口令需告知用户（一次性，与恢复码同批）
    if generated_pw:
        _persist_initial_password(generated_pw, admin_username)

    logger.info("vault setup completed (admin=%s)", admin_username)
    return SetupResult(
        recovery_code=recovery_display,
        admin_username=admin_username,
        admin_password=generated_pw,
        message="Setup completed. Save the recovery code offline; it is shown only once.",
    )


# ── unlock（PRD §4.1）────────────────────────────────────────────────────────


@dataclass
class UnlockResult:
    state: str                  # "UNLOCKED"
    access_token: str | None    # 口令解锁时签发；恢复码解锁为 None
    refresh_token: str | None
    needs_login: bool           # 恢复码解锁后需用真实管理员口令登录
    username: str | None


def unlock(
    *,
    username: str | None = None,
    password: str | None = None,
    recovery_code: str | None = None,
) -> UnlockResult:
    """解锁核心。

    口令路径：username + password → 解 DEK + 库内 argon2 校验 + 签发 JWT。
    恢复码路径：recovery_code → 仅解 DEK + 切 UNLOCKED（needs_login=True）。

    失败统一抛 UnlockError（不区分用户不存在 / 口令错），并计入防爆破。
    """
    if needs_setup():
        raise LockStateError("Vault not initialized; run setup first")

    _check_rate_limit()  # 锁定窗口内直接拒
    ks = crypto.load_keystore(keystore_path())

    dek: bytes
    is_recovery = bool(recovery_code)
    try:
        if is_recovery:
            dek = crypto.unwrap_for_recovery(ks, recovery_code)  # type: ignore[arg-type]
        else:
            if not username or not password:
                raise InvalidTag("missing credentials")
            dek = crypto.unwrap_for_user(ks, username, password)
    except InvalidTag:
        _record_failure()
        raise UnlockError("Unlock failed")

    dek_hex = dek.hex()
    crypto.secure_wipe(dek)

    # 解包成功 → 初始化引擎 + 首次迁移
    try:
        database.init_engine(dek_hex)
        if not keyvault.has_migrated():
            run_migrations()
    except Exception:
        logger.error("engine init / migration failed after successful DEK unwrap", exc_info=True)
        database.shutdown_engine()
        raise UnlockError("Unlock failed")

    keyvault.unlock_with_dek(dek_hex)
    _reset_attempts()

    # 恢复码路径：解开即止，不签发用户 token
    if is_recovery:
        logger.info("vault unlocked via recovery code (login required)")
        return UnlockResult(
            state="UNLOCKED", access_token=None, refresh_token=None,
            needs_login=True, username=None,
        )

    # 口令路径：库内 argon2 二次校验 + 签发 JWT（单口令体验）
    assert username is not None and password is not None
    access_token, refresh_token = _issue_token_for(database.SessionLocal(), username, password)  # type: ignore[arg-type]
    logger.info("vault unlocked and session issued (user=%s)", username)
    return UnlockResult(
        state="UNLOCKED", access_token=access_token, refresh_token=refresh_token,
        needs_login=False, username=username,
    )


def _issue_token_for(db: Session, username: str, password: str) -> tuple[str, str]:
    """库内 argon2 校验口令并签发 JWT（PRD §4.1.5）。失败转 UnlockError。"""
    user = user_repo.get_by_username(db, username)
    if user is None or user.status == "disabled" or not verify_password(password, user.password_hash):
        # 解锁成功但库内口令不一致（罕见：keystore 与库脱节）—— 视为解锁失败
        raise UnlockError("Unlock failed")
    timeout = get_session_timeout_minutes(db)
    access = create_access_token(user.id, user.role, expire_minutes=timeout, token_version=user.token_version or 0)
    refresh = create_refresh_token(user.id, user.role, token_version=user.token_version or 0)
    return access, refresh


# ── 改密重新包裹（PRD §5.3）─────────────────────────────────────────────────


def change_password_and_rewrap(
    db: Session, user: User, old_password: str, new_password: str
) -> None:
    """改密：库内 argon2 哈希与 keystore 记录原子同步。

    必须在 UNLOCKED（DEK 可得）下执行。先取运行态 DEK，用新口令重新包裹；
    库内哈希先提交，再替换 keystore 记录；keystore 写失败则回滚库内哈希。
    """
    if not keyvault.is_unlocked():
        raise LockStateError("Vault must be unlocked to change password")
    if old_password == new_password:
        raise ValidationError("New password cannot be the same as the old password")
    if not verify_password(old_password, user.password_hash):
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Incorrect old password")

    dek_hex = keyvault.get_dek_hex()
    if not dek_hex:
        raise LockStateError("No DEK available")
    dek = bytes.fromhex(dek_hex)

    # 1) 库内：更新口令哈希（尚未提交）
    old_hash = user.password_hash
    user_repo.update_password(db, user, hash_password(new_password))
    db.flush()

    # 2) keystore：用新口令重新包裹同一 DEK
    try:
        ks = crypto.load_keystore(keystore_path())
        ks.upsert(crypto.build_user_record(dek, user.username, new_password))
        crypto.save_keystore(keystore_path(), ks)
    except Exception:
        # keystore 写失败 → 回滚库内哈希
        user.password_hash = old_hash
        db.rollback()
        crypto.secure_wipe(dek)
        logger.error("keystore rewrap failed; rolled back in-db password hash", exc_info=True)
        raise
    finally:
        crypto.secure_wipe(dek)

    # 3) 提交库内哈希（keystore 已落盘）
    db.commit()
    logger.info("password changed and DEK rewrapped (user=%s)", user.username)


# ── 增 / 删管理员入册（PRD §5.4）─────────────────────────────────────────────


def register_admin(username: str, initial_password: str) -> None:
    """在 UNLOCKED 态用新管理员初始口令包裹 DEK，加 keystore 记录。

    库内用户行的创建由 user 管理路由负责；本函数只同步 keystore 入册。
    """
    if not keyvault.is_unlocked():
        raise LockStateError("Vault must be unlocked to register an admin")
    dek_hex = keyvault.get_dek_hex()
    dek = bytes.fromhex(dek_hex)  # type: ignore[arg-type]
    try:
        ks = crypto.load_keystore(keystore_path())
        ks.upsert(crypto.build_user_record(dek, username, initial_password))
        crypto.save_keystore(keystore_path(), ks)
    finally:
        crypto.secure_wipe(dek)
    logger.info("admin registered into keystore (user=%s)", username)


def unregister_admin(username: str) -> bool:
    """移除某管理员的 keystore 记录（其口令立即失效）。库内禁用由调用方处理。"""
    ks = crypto.load_keystore(keystore_path())
    removed = ks.remove(crypto.user_kid(username))
    if removed:
        crypto.save_keystore(keystore_path(), ks)
        logger.info("admin removed from keystore (user=%s)", username)
    return removed


def admin_has_keystore_record(username: str) -> bool:
    """某用户是否已在 keystore 入册（可解锁）。"""
    if needs_setup():
        return False
    ks = crypto.load_keystore(keystore_path())
    return ks.get(crypto.user_kid(username)) is not None


# ── 辅助 ──────────────────────────────────────────────────────────────────────


def _safe_remove(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        logger.warning("failed to remove %s: %s", path, exc)
