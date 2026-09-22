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


# ── Network Interface Schemas (P0) ───────────────────────────────

class NetworkInterfaceBase(BaseModel):
    """Shared network interface fields (all optional on the wire)."""
    name: str | None = Field(None, max_length=64)
    mac_address: str | None = Field(None, max_length=32)
    ip_address: str | None = Field(None, max_length=45)
    cidr_prefix: int | None = Field(None, ge=0, le=128)
    vlan_id: int | None = Field(None, ge=1, le=4094)
    gateway: str | None = Field(None, max_length=45)
    role: str | None = Field(None, pattern="^(data|mgmt|other)$")
    bond_master: str | None = Field(None, max_length=64)
    is_primary: bool | None = None
    status: str | None = Field(None, pattern="^(active|disconnected)$")
    # Port-level upstream connection
    connected_asset_id: int | None = None
    connected_port: str | None = Field(None, max_length=64)


class NetworkInterfaceCreate(NetworkInterfaceBase):
    """Create a network interface record."""


class NetworkInterfaceRead(NetworkInterfaceBase):
    model_config = {"from_attributes": True}

    id: int
    asset_id: int
    role: str = "data"
    is_primary: bool = False
    status: str = "active"
    created_at: datetime
    updated_at: datetime


# ── Asset request Schemas ────────────────────────────────────────

AssetType = Literal[
    "physical", "virtual", "network_device", "other", "cloud_server",
    "storage", "security_device", "load_balancer",
]
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
    # P0 hardware identity
    serial_number: str | None = Field(None, max_length=128)
    vendor: str | None = Field(None, max_length=128)
    hardware_model: str | None = Field(None, max_length=128)
    asset_tag: str | None = Field(None, max_length=64)
    location: str = Field(..., max_length=255)
    # P0 structured location
    datacenter: str | None = Field(None, max_length=128)
    rack: str | None = Field(None, max_length=64)
    rack_u_start: int | None = Field(None, ge=0, le=100)
    rack_u_height: int | None = Field(None, ge=1, le=10)
    owner: str = Field(..., max_length=100)
    business_system: str = Field(..., max_length=100)
    importance: Importance
    network_zone: NetworkZone
    # P0 out-of-band / cloud identity
    mgmt_ip: str | None = Field(None, max_length=45)
    cloud_instance_id: str | None = Field(None, max_length=128)
    cloud_region: str | None = Field(None, max_length=64)
    cloud_zone: str | None = Field(None, max_length=64)
    cloud_spec: str | None = Field(None, max_length=128)
    hypervisor: str | None = Field(None, max_length=128)
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
    # P0 hardware identity
    serial_number: str | None = Field(None, max_length=128)
    vendor: str | None = Field(None, max_length=128)
    hardware_model: str | None = Field(None, max_length=128)
    asset_tag: str | None = Field(None, max_length=64)
    location: str | None = Field(None, max_length=255)
    # P0 structured location
    datacenter: str | None = Field(None, max_length=128)
    rack: str | None = Field(None, max_length=64)
    rack_u_start: int | None = Field(None, ge=0, le=100)
    rack_u_height: int | None = Field(None, ge=1, le=10)
    owner: str | None = Field(None, max_length=100)
    business_system: str | None = Field(None, max_length=100)
    importance: Importance | None = None
    network_zone: NetworkZone | None = None
    # P0 out-of-band / cloud identity
    mgmt_ip: str | None = Field(None, max_length=45)
    cloud_instance_id: str | None = Field(None, max_length=128)
    cloud_region: str | None = Field(None, max_length=64)
    cloud_zone: str | None = Field(None, max_length=64)
    cloud_spec: str | None = Field(None, max_length=128)
    hypervisor: str | None = Field(None, max_length=128)
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
    # P0 hardware identity
    serial_number: str | None = None
    vendor: str | None = None
    hardware_model: str | None = None
    asset_tag: str | None = None
    location: str
    # P0 structured location
    datacenter: str | None = None
    rack: str | None = None
    rack_u_start: int | None = None
    rack_u_height: int | None = None
    rack_id: int | None = None
    owner: str
    business_system: str
    importance: str
    network_zone: str
    # P0 out-of-band / cloud identity
    mgmt_ip: str | None = None
    cloud_instance_id: str | None = None
    cloud_region: str | None = None
    cloud_zone: str | None = None
    cloud_spec: str | None = None
    hypervisor: str | None = None
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
    interfaces: list[NetworkInterfaceRead] = []
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
    # Datacenter lets the UI filter peer devices in the same datacenter
    datacenter: str | None = None
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
