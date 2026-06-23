"""
LLM API Key encrypted storage
Uses Fernet symmetric encryption (simplified envelope encryption)
Master key is read from the LLM_MASTER_KEY environment variable
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _get_master_key() -> bytes:
    """
    Get the master key from environment variables.
    If not set, derive it from JWT_SECRET (development environment fallback).
    """
    raw = os.environ.get("LLM_MASTER_KEY", "")
    if not raw:
        # Fallback: derive from JWT_SECRET
        from app.core.config import settings
        raw = settings.jwt_secret
    # Fernet requires a 32-byte base64-encoded key
    # Use SHA-256 hash to ensure consistent length
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string and return the ciphertext (base64 encoded)"""
    if not plaintext:
        return ""
    key = _get_master_key()
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a string and return the plaintext. Returns empty string on failure."""
    if not ciphertext:
        return ""
    key = _get_master_key()
    f = Fernet(key)
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        import logging
        logging.getLogger(__name__).warning(
            "decrypt_value failed (InvalidToken); returning empty string. "
            "Likely a master-key change or corrupted ciphertext."
        )
        return ""
    except Exception:
        import logging
        logging.getLogger(__name__).warning("decrypt_value unexpected error; returning empty string")
        return ""
