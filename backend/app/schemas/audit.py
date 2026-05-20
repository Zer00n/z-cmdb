"""
审计日志 Pydantic Schema
"""
from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    timestamp: datetime
    user_id: int | None
    username: str | None
    user_role: str | None
    action_type: str
    target_type: str | None
    target_id: str | None
    ip_address: str | None
    user_agent: str | None
    details: str | None
    result: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
