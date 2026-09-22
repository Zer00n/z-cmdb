"""
LLM API Key encrypted storage — Fernet symmetric encryption.

密钥分离（v0.6.6 安全修复）：
  - 字段加密主密钥必须独立于 JWT_SECRET：优先取环境变量 ``LLM_MASTER_KEY``，
    其次取数据目录下的 0600 密钥文件 ``llm_master.key``；
  - 生产环境两者皆缺失时失效关闭（fail-closed）；开发/测试环境才回退 JWT_SECRET；
  - 密文带密钥版本前缀（如 ``v1:``），无前缀的历史令牌按 v0（JWT 派生密钥）
    解密，使存量密文在自动迁移前仍可读，轮换密钥也不会静默使密文失效。
"""
import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

CURRENT_KID = "v1"   # 当前密钥版本
LEGACY_KID = "v0"     # 历史版本：Fernet(sha256(JWT_SECRET))

logger = logging.getLogger(__name__)


def _fernet_key(raw: str) -> bytes:
    """Fernet 需要 32 字节 base64 密钥；用 SHA-256 规整任意长度输入。"""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _current_key() -> bytes:
    """当前版本字段主密钥：LLM_MASTER_KEY 环境变量 → data/llm_master.key
    → 生产 fail-closed → 开发环境 JWT 回退（仅用于不含真实机密的本地开发）。"""
    raw = os.environ.get("LLM_MASTER_KEY", "")
    if not raw:
        from app.core.config import settings

        key_file = settings.db_path.parent / "llm_master.key"
        if key_file.exists():
            raw = key_file.read_text(encoding="utf-8").strip()
        elif settings.APP_ENV.lower() in ("production", "prod"):
            raise RuntimeError(
                "LLM_MASTER_KEY (or data/llm_master.key) must be configured "
                "independently of JWT_SECRET"
            )
        else:
            raw = settings.jwt_secret
    return _fernet_key(raw)


def _key_for_id(kid: str) -> bytes:
    if kid == CURRENT_KID:
        return _current_key()
    if kid == LEGACY_KID:
        from app.core.config import settings

        return _fernet_key(settings.jwt_secret)
    raise RuntimeError(f"unknown encryption key id: {kid}")


def _assert_key_available() -> None:
    """生产环境全局门禁：独立主密钥（env 或密钥文件）必须存在，否则 fail-closed。
    setup/unlock 会在任何字段加解密之前生成密钥文件，故不影响正常业务。"""
    if os.environ.get("LLM_MASTER_KEY"):
        return
    from app.core.config import settings

    if settings.APP_ENV.lower() in ("production", "prod"):
        if not (settings.db_path.parent / "llm_master.key").exists():
            raise RuntimeError(
                "LLM_MASTER_KEY (or data/llm_master.key) must be configured "
                "independently of JWT_SECRET"
            )


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string and return version-tagged ciphertext."""
    if not plaintext:
        return ""
    _assert_key_available()
    token = Fernet(_current_key()).encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{CURRENT_KID}:{token}"


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a version-tagged or legacy ciphertext. Returns "" on failure."""
    if not ciphertext:
        return ""
    _assert_key_available()
    # Fernet 令牌为 base64url（不含 ':'），故 ':' 只可能是版本前缀分隔符
    if ":" in ciphertext:
        kid, token = ciphertext.split(":", 1)
    else:
        kid, token = LEGACY_KID, ciphertext
    fernet = Fernet(_key_for_id(kid))
    try:
        return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning(
            "decrypt_value failed (InvalidToken); returning empty string. "
            "Likely a master-key change or corrupted ciphertext."
        )
        return ""
    except Exception:
        logger.warning("decrypt_value unexpected error; returning empty string", exc_info=True)
        return ""
