"""
Scan batch related Pydantic v2 schemas
"""
from datetime import datetime

from pydantic import BaseModel


class ScanBatchRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    batch_name: str | None
    uploaded_by: int | None
    uploaded_at: datetime
    scan_started_at: datetime | None
    scan_finished_at: datetime | None
    file_size_bytes: int | None
    total_hosts: int | None
    new_count: int
    changed_count: int
    missing_count: int
    status: str


class ScanBatchListResponse(BaseModel):
    items: list[ScanBatchRead]
    total: int


class ScanConfirmRequest(BaseModel):
    """Confirm import request: contains supplementary fields for new assets"""
    new_assets: list[dict] = []


# ── Diff detail Schemas ─────────────────────────────────────────


class DiffPortRead(BaseModel):
    """Port-level diff"""
    port_number: int
    protocol: str
    service_name: str | None = None
    service_version: str | None = None
    state: str | None = None


class DiffHostPortChange(BaseModel):
    """Port change detail"""
    port_number: int
    protocol: str
    old_service: str | None = None
    new_service: str | None = None
    old_version: str | None = None
    new_version: str | None = None
    old_state: str | None = None
    new_state: str | None = None
    change_type: str = ""  # added / removed / modified


class DiffNewHost(BaseModel):
    """Newly discovered host"""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    os_info: str | None = None
    ports: list[DiffPortRead] = []


class DiffChangedHost(BaseModel):
    """Changed host"""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    os_info: str | None = None
    matched_asset_id: int | None = None
    matched_asset_no: str | None = None
    port_changes: list[DiffHostPortChange] = []
    current_ports: list[DiffPortRead] = []
    scan_ports: list[DiffPortRead] = []


class DiffMissingHost(BaseModel):
    """Missing host"""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    matched_asset_id: int | None = None
    matched_asset_no: str | None = None
    missing_count: int = 0


class ScanDiffResponse(BaseModel):
    """Scan batch diff detail"""
    batch_id: int
    batch_name: str | None = None
    status: str
    total_hosts: int
    new_count: int
    changed_count: int
    missing_count: int
    new_hosts: list[DiffNewHost] = []
    changed_hosts: list[DiffChangedHost] = []
    missing_hosts: list[DiffMissingHost] = []
