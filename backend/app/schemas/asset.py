"""
Asset-related Pydantic v2 schemas
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Port Schemas ─────────────────────────────────────────────────

class AssetPortRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    port_number: int
    protocol: str
    service_name: str | None
    service_version: str | None
    state: str | None
    last_seen_at: datetime | None


# ── Asset request Schemas ────────────────────────────────────────

AssetType = Literal["physical", "virtual", "network_device", "other", "cloud_server"]
Importance = Literal["core", "important", "normal"]
NetworkZone = Literal[
    "dmz", "intranet", "office", "management", "other",
    "aliyun", "tencent", "huawei", "aws", "azure", "gcp", "other_cloud",
]
AssetStatus = Literal["online", "offline", "decommissioned"]
AssetSource = Literal["scan", "manual", "excel"]


class AssetCreate(BaseModel):
    """Create asset (manual entry)"""
    asset_no: str | None = Field(None, max_length=64, description="Leave empty to auto-generate")
    ip_address: str = Field(..., max_length=45)
    mac_address: str | None = Field(None, max_length=32)
    hostname: str | None = Field(None, max_length=255)
    asset_type: AssetType
    os_info: str | None = Field(None, max_length=255)
    location: str = Field(..., max_length=255)
    owner: str = Field(..., max_length=100)
    business_system: str = Field(..., max_length=100)
    importance: Importance
    network_zone: NetworkZone
    cpu: str | None = Field(None, max_length=100)
    memory_gb: int | None = Field(None, ge=0)
    disk_gb: int | None = Field(None, ge=0)
    purchase_date: str | None = Field(None, max_length=20)
    warranty_expiry: str | None = Field(None, max_length=20)
    remark: str | None = None
    source: AssetSource = "manual"
    # V0.4 cost fields
    purchase_price: float | None = None
    depreciation_months: int | None = None
    residual_rate: float | None = None
    depreciation_method: str | None = None
    end_of_life_strategy: str | None = None
    revalue_amount: float | None = None
    revalue_months: int | None = None
    billing_mode: str | None = None
    responsible_dept_id: int | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        try:
            ipaddress.IPv4Address(v)
        except ValueError as exc:
            raise ValueError(f"Invalid IPv4 address: {v}") from exc
        return v


class AssetUpdate(BaseModel):
    """Update asset (PATCH, all fields optional)"""
    ip_address: str | None = Field(None, max_length=45)
    mac_address: str | None = Field(None, max_length=32)
    hostname: str | None = Field(None, max_length=255)
    asset_type: AssetType | None = None
    os_info: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    owner: str | None = Field(None, max_length=100)
    business_system: str | None = Field(None, max_length=100)
    importance: Importance | None = None
    network_zone: NetworkZone | None = None
    cpu: str | None = Field(None, max_length=100)
    memory_gb: int | None = Field(None, ge=0)
    disk_gb: int | None = Field(None, ge=0)
    purchase_date: str | None = Field(None, max_length=20)
    warranty_expiry: str | None = Field(None, max_length=20)
    remark: str | None = None
    status: AssetStatus | None = None
    # V0.4 cost fields
    purchase_price: float | None = None
    depreciation_months: int | None = None
    residual_rate: float | None = None
    depreciation_method: str | None = None
    end_of_life_strategy: str | None = None
    revalue_amount: float | None = None
    revalue_months: int | None = None
    billing_mode: str | None = None
    responsible_dept_id: int | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import ipaddress
        try:
            ipaddress.IPv4Address(v)
        except ValueError as exc:
            raise ValueError(f"Invalid IPv4 address: {v}") from exc
        return v


# ── Asset response Schemas ───────────────────────────────────────

class AssetRead(BaseModel):
    """Asset list/detail response"""
    model_config = {"from_attributes": True}

    id: int
    asset_no: str
    ip_address: str
    mac_address: str | None
    hostname: str | None
    asset_type: str
    os_info: str | None
    location: str
    owner: str
    business_system: str
    importance: str
    network_zone: str
    cpu: str | None
    memory_gb: int | None
    disk_gb: int | None
    purchase_date: str | None
    warranty_expiry: str | None
    remark: str | None
    status: str
    source: str
    last_seen_at: datetime | None
    missing_count: int
    last_scan_batch_id: int | None
    created_at: datetime
    updated_at: datetime
    ports: list[AssetPortRead] = []
    # V0.4 cost fields
    purchase_price: float | None = None
    depreciation_months: int | None = None
    residual_rate: float | None = None
    depreciation_method: str | None = None
    end_of_life_strategy: str | None = None
    revalue_amount: float | None = None
    revalue_months: int | None = None
    revalue_effective_date: str | None = None
    billing_mode: str | None = None
    responsible_dept_id: int | None = None


class AssetListItem(BaseModel):
    """Asset list row (compact, without port details)"""
    model_config = {"from_attributes": True}

    id: int
    asset_no: str
    ip_address: str
    mac_address: str | None
    hostname: str | None
    asset_type: str
    os_info: str | None
    location: str
    owner: str
    business_system: str
    importance: str
    network_zone: str
    status: str
    source: str
    last_seen_at: datetime | None
    missing_count: int
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    """Paginated asset list response"""
    items: list[AssetListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Query parameter Schemas ──────────────────────────────────────

class AssetQueryParams(BaseModel):
    """Asset list query parameters"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100000)
    search: str | None = None          # Full-text search: IP / hostname / asset number / remark
    asset_type: AssetType | None = None
    network_zone: NetworkZone | None = None
    importance: Importance | None = None
    status: AssetStatus | None = None
    business_system: str | None = None
    owner: str | None = None
    source: AssetSource | None = None
