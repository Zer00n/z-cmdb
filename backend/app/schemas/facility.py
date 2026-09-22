"""Facility (datacenter / rack / rack elevation) schemas."""
from pydantic import BaseModel, Field


# ── Rack CRUD ────────────────────────────────────────────────────

class RackCreate(BaseModel):
    datacenter: str | None = Field(None, max_length=128)
    name: str = Field(..., max_length=64)
    u_height: int = Field(42, ge=1, le=52)
    room: str | None = Field(None, max_length=128)
    row_label: str | None = Field(None, max_length=64)
    col_label: str | None = Field(None, max_length=64)
    description: str | None = None


class RackUpdate(BaseModel):
    datacenter: str | None = Field(None, max_length=128)
    name: str | None = Field(None, max_length=64)
    u_height: int | None = Field(None, ge=1, le=52)
    room: str | None = Field(None, max_length=128)
    row_label: str | None = Field(None, max_length=64)
    col_label: str | None = Field(None, max_length=64)
    description: str | None = None


class RackRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    datacenter: str | None
    name: str
    u_height: int
    room: str | None
    row_label: str | None
    col_label: str | None
    description: str | None


# ── Aggregated views ─────────────────────────────────────────────

class ConnectedSwitch(BaseModel):
    id: int
    asset_no: str
    hostname: str | None
    asset_type: str


class DeviceInterface(BaseModel):
    id: int
    name: str | None
    mac_address: str | None
    ip_address: str | None
    role: str
    vlan_id: int | None
    bond_master: str | None
    is_primary: bool
    connected_asset_id: int | None
    connected_port: str | None
    connected_switch: ConnectedSwitch | None = None
    source: str = "port"  # port = port-level cabling; asset = device-level fallback


class ElevationDevice(BaseModel):
    id: int
    asset_no: str
    hostname: str | None
    asset_type: str
    importance: str
    status: str
    u_start: int | None
    u_height: int | None
    interfaces: list[DeviceInterface] = []


class RackWarning(BaseModel):
    code: str            # out_of_range / overlap / missing_u_start
    message: str
    asset_id: int | None = None


class RackElevation(RackRead):
    devices: list[ElevationDevice] = []
    warnings: list[RackWarning] = []


class RackSummary(BaseModel):
    id: int
    name: str
    u_height: int
    device_count: int
    used_u: int
    utilization: float


class UnlocatedAsset(BaseModel):
    id: int
    asset_no: str
    hostname: str | None
    ip_address: str
    reason: str          # no_rack / no_u_start


class DatacenterRacks(BaseModel):
    datacenter: str
    racks: list[RackSummary]
    unlocated: list[UnlocatedAsset] = []


class DatacenterSummary(BaseModel):
    datacenter: str
    rack_count: int
    device_count: int
    used_u: int
    total_u: int
    utilization: float
    unlocated_count: int
