"""
V0.6 project-perspective Pydantic v2 schemas
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Project Schemas ───────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    owner: str | None = Field(None, max_length=100)
    business_unit: str | None = Field(None, max_length=100)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    owner: str | None = Field(None, max_length=100)
    business_unit: str | None = Field(None, max_length=100)
    billing_enabled: int | None = Field(None, ge=0, le=1)


class ProjectRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    business_unit: str | None
    owner: str | None
    billing_enabled: int
    created_at: datetime
    updated_at: datetime


class ProjectListItem(BaseModel):
    """Compact project for list view with aggregated fields"""
    model_config = {"from_attributes": True}

    id: str
    name: str
    business_unit: str | None
    owner: str | None
    billing_enabled: int
    unit_count: int = 0
    host_count: int = 0
    current_month_cost: float | None = None
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
