"""
LLM API Key 加密存储
使用 Fernet 对称加密（envelope encryption 简化版）
主密钥从环境变量 LLM_MASTER_KEY 读取
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _get_master_key() -> bytes:
    """
    从环境变量获取主密钥。
    如果未设置，使用 JWT_SECRET 派生（开发环境兜底）。
    """
    raw = os.environ.get("LLM_MASTER_KEY", "")
    if not raw:
        # 兜底：用 JWT_SECRET 派生
        from app.core.config import settings
        raw = settings.jwt_secret
    # Fernet 需要 32 字节 base64 编码的 key
    # 用 SHA256 哈希确保长度一致
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """加密字符串，返回密文（base64 编码）"""
    if not plaintext:
        return ""
    key = _get_master_key()
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """解密字符串，返回明文。解密失败返回空字符串。"""
    if not ciphertext:
        return ""
    key = _get_master_key()
    f = Fernet(key)
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        # 可能是旧的明文数据，直接返回
        return ciphertext
