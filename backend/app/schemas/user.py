"""
用户相关 Pydantic v2 Schema
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── 请求 Schema ──────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """密码策略：最小 12 位，必含大小写数字符号"""
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(not c.isalnum() for c in v)
        if not (has_upper and has_lower and has_digit and has_symbol):
            raise ValueError("密码必须包含大写字母、小写字母、数字和特殊符号")
        return v


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=12, max_length=128)
    role: Literal["super_admin", "admin", "auditor"] = "admin"
    full_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(not c.isalnum() for c in v)
        if not (has_upper and has_lower and has_digit and has_symbol):
            raise ValueError("密码必须包含大写字母、小写字母、数字和特殊符号")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=100)
    role: Literal["super_admin", "admin", "auditor"] | None = None
    status: Literal["active", "disabled"] | None = None


# ── 响应 Schema ──────────────────────────────────────────────


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    role: str
    full_name: str | None
    email: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class TokenPayload(BaseModel):
    sub: int          # user_id
    role: str
    exp: int
