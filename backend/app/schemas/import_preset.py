"""
Import Preset Pydantic schemas
"""
from enum import Enum

from pydantic import BaseModel, Field


class PresetCategory(str, Enum):
    location = "location"
    owner = "owner"
    business_system = "business_system"


class PresetCreate(BaseModel):
    category: PresetCategory
    value: str = Field(min_length=1, max_length=255)
    is_default: bool = False
    sort_order: int = 0
    remark: str | None = None


class PresetUpdate(BaseModel):
    value: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = None
    remark: str | None = None


class PresetOut(BaseModel):
    id: int
    category: PresetCategory
    value: str
    is_default: bool
    sort_order: int
    remark: str | None

    model_config = {"from_attributes": True}


class SyncResult(BaseModel):
    location: int
    owner: int
    business_system: int
