"""
Application/service inventory Pydantic v2 schemas
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AppSource = Literal["manual", "scan"]
AppStatus = Literal["active", "decommissioned"]


class AssetAppCreate(BaseModel):
    """Create application"""
    name: str = Field(..., max_length=100, description="Application name, e.g. nginx, mysql-server")
    version: str | None = Field(None, max_length=100, description="Version number")
    category: str | None = Field(None, max_length=50, description="Application category")
    port: int | None = Field(None, ge=1, le=65535, description="Primary listening port")
    protocol: str | None = Field(None, pattern=r"^(tcp|udp)$", description="Protocol tcp/udp")
    install_path: str | None = Field(None, max_length=255, description="Installation path")
    config_path: str | None = Field(None, max_length=255, description="Configuration file path")
    notes: str | None = Field(None, description="Notes")


class AssetAppUpdate(BaseModel):
    """Update application (PATCH, all fields optional)"""
    name: str | None = Field(None, max_length=100)
    version: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=50)
    port: int | None = Field(None, ge=1, le=65535)
    protocol: str | None = Field(None, pattern=r"^(tcp|udp)$")
    install_path: str | None = Field(None, max_length=255)
    config_path: str | None = Field(None, max_length=255)
    notes: str | None = None
    status: AppStatus | None = None


class AssetAppRead(BaseModel):
    """Application response"""
    model_config = {"from_attributes": True}

    id: int
    asset_id: int
    name: str
    version: str | None
    category: str | None
    port: int | None
    protocol: str | None
    install_path: str | None
    config_path: str | None
    notes: str | None
    source: str
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: int | None


class AssetAppListResponse(BaseModel):
    """Application list response"""
    items: list[AssetAppRead]
    total: int


class AppSearchItem(BaseModel):
    """Global application search result item"""
    model_config = {"from_attributes": True}

    id: int
    asset_id: int
    name: str
    version: str | None
    category: str | None
    port: int | None
    # Associated asset info
    asset_no: str
    ip_address: str
    hostname: str | None


class AppSearchResponse(BaseModel):
    """Global application search response"""
    items: list[AppSearchItem]
    total: int
