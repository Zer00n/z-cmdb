"""
资产相关 Pydantic v2 Schema
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── 端口 Schema ──────────────────────────────────────────────

class AssetPortRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    port_number: int
    protocol: str
    service_name: str | None
    service_version: str | None
    state: str | None
    last_seen_at: datetime | None


# ── 资产请求 Schema ──────────────────────────────────────────

AssetType = Literal["physical", "virtual", "network_device", "other"]
Importance = Literal["core", "important", "normal"]
NetworkZone = Literal["dmz", "intranet", "office", "management", "other"]
AssetStatus = Literal["online", "offline", "decommissioned"]
AssetSource = Literal["scan", "manual"]


class AssetCreate(BaseModel):
    """新增资产（手动录入）"""
    asset_no: str | None = Field(None, max_length=64, description="留空则自动生成")
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

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        try:
            ipaddress.IPv4Address(v)
        except ValueError as exc:
            raise ValueError(f"无效的 IPv4 地址: {v}") from exc
        return v


class AssetUpdate(BaseModel):
    """更新资产（PATCH，所有字段可选）"""
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

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import ipaddress
        try:
            ipaddress.IPv4Address(v)
        except ValueError as exc:
            raise ValueError(f"无效的 IPv4 地址: {v}") from exc
        return v


# ── 资产响应 Schema ──────────────────────────────────────────

class AssetRead(BaseModel):
    """资产列表/详情响应"""
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


class AssetListItem(BaseModel):
    """资产列表行（精简版，不含端口详情）"""
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
    """资产列表分页响应"""
    items: list[AssetListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── 查询参数 Schema ──────────────────────────────────────────

class AssetQueryParams(BaseModel):
    """资产列表查询参数"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100000)
    search: str | None = None          # 全文搜索：IP/主机名/资产编号/备注
    asset_type: AssetType | None = None
    network_zone: NetworkZone | None = None
    importance: Importance | None = None
    status: AssetStatus | None = None
    business_system: str | None = None
    owner: str | None = None
    source: AssetSource | None = None
