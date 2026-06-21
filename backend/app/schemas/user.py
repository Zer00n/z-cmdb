"""
User-related Pydantic v2 schemas
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request Schemas ──────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Password policy: minimum 12 characters, must include upper/lower/digit/symbol"""
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(not c.isalnum() for c in v)
        if not (has_upper and has_lower and has_digit and has_symbol):
            raise ValueError("Password must contain uppercase, lowercase, digit, and special character")
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
            raise ValueError("Password must contain uppercase, lowercase, digit, and special character")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=100)
    role: Literal["super_admin", "admin", "auditor"] | None = None
    status: Literal["active", "disabled"] | None = None


# ── Response Schemas ─────────────────────────────────────────────


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
