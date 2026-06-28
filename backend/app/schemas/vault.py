"""
Vault (SQLite 静态加密) 相关的 Pydantic v2 schema：
解锁状态、首次 setup、解锁请求/响应。
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _password_policy(v: Optional[str]) -> Optional[str]:
    """口令策略：>=12 字符，含大小写+数字+特殊。None 表示不提供（系统生成）。"""
    if v is None:
        return v
    if len(v) < 12:
        raise ValueError("Password must be at least 12 characters")
    has_upper = any(c.isupper() for c in v)
    has_lower = any(c.islower() for c in v)
    has_digit = any(c.isdigit() for c in v)
    has_symbol = any(not c.isalnum() for c in v)
    if not (has_upper and has_lower and has_digit and has_symbol):
        raise ValueError("Password must include upper/lower letters, a digit and a symbol")
    return v


class LockStatusResponse(BaseModel):
    state: str  # "LOCKED" | "UNLOCKED"
    needs_setup: bool


class SetupRequest(BaseModel):
    username: str = Field("admin", min_length=1, max_length=64)
    password: Optional[str] = Field(None, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_policy(cls, v: Optional[str]) -> Optional[str]:
        return _password_policy(v)


class SetupResponse(BaseModel):
    recovery_code: str          # 一次性恢复码（展示串）
    admin_username: str
    admin_password: Optional[str] = None  # 仅系统随机生成时返回（一次性）
    message: str


class UnlockRequest(BaseModel):
    username: Optional[str] = Field(None, max_length=64)
    password: Optional[str] = None
    recovery_code: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "UnlockRequest":
        if self.recovery_code:
            return self
        if self.username and self.password:
            return self
        raise ValueError("Provide (username + password) or recovery_code")


class UnlockResponse(BaseModel):
    state: str  # "UNLOCKED"
    access_token: Optional[str] = None
    needs_login: bool = False
    username: Optional[str] = None
