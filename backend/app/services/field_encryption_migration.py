"""
字段密文一次性迁移：v0（无版本前缀、密钥派生自 JWT_SECRET）→ v1（独立主密钥）。

在 setup / unlock 成功、引擎就绪后由 key_service 调用；幂等，可重复执行。
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import CURRENT_KID, decrypt_value, encrypt_value
from app.models.config import SystemConfig

logger = logging.getLogger(__name__)


def migrate_legacy_field_ciphertext(db: Session) -> int:
    """将所有无版本前缀的 api_key 密文用当前主密钥重新加密，返回迁移条数。"""
    migrated = 0
    configs = db.scalars(
        select(SystemConfig).where(SystemConfig.key.like("%api_key%"))
    ).all()
    for cfg in configs:
        if cfg.value and ":" not in cfg.value:  # 无版本前缀 → 历史 v0 密文
            plaintext = decrypt_value(cfg.value)
            if plaintext:
                cfg.value = encrypt_value(plaintext)
                migrated += 1
    if migrated:
        db.commit()
        logger.info(
            "migrated %d legacy field ciphertext(s) to %s", migrated, CURRENT_KID
        )
    return migrated
