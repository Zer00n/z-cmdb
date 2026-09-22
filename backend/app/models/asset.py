"""
Asset SQLAlchemy model
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Business primary key
    asset_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # Network identifiers
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    mac_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Classification
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    os_info: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── P0: hardware identity (unique physical / cloud identity) ──
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hardware_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    asset_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Location and ownership
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    # ── P0: structured rack location (free-text location is kept as the fallback/display) ──
    datacenter: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rack: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rack_u_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rack_u_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Resolved rack entity (auto-merged from datacenter + rack text on save)
    rack_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("racks.id", ondelete="SET NULL"), nullable=True
    )

    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    business_system: Mapped[str] = mapped_column(String(100), nullable=False)

    # Importance and network zone
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    network_zone: Mapped[str] = mapped_column(String(32), nullable=False)

    # ── P0: out-of-band management (IPMI / iDRAC / iLO / BMC) ──
    mgmt_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # ── P0: cloud / virtualization identity ──
    cloud_instance_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cloud_region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cloud_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cloud_spec: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hypervisor: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Hardware info (optional)
    cpu: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Procurement info (optional)
    purchase_date: Mapped[str | None] = mapped_column(String(20), nullable=True)   # ISO date string
    warranty_expiry: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Remarks
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # V0.4 cost accounting fields (optional; no impact on existing logic when feature is off)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    depreciation_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    depreciation_method: Mapped[str | None] = mapped_column(String(20), nullable=True, default="straight_line")
    end_of_life_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True, default="zero")
    revalue_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    revalue_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revalue_effective_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    billing_mode: Mapped[str | None] = mapped_column(String(20), nullable=True, default="cost")
    responsible_dept_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    # Status and source
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    # Scan-related fields (system-managed)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scan_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Associated ports
    ports: Mapped[list["AssetPort"]] = relationship(
        "AssetPort", back_populates="asset", cascade="all, delete-orphan"
    )

    # Associated apps (v2.5)
    apps: Mapped[list["AssetApp"]] = relationship(
        "AssetApp", back_populates="asset", cascade="all, delete-orphan"
    )

    # P0: network interfaces (multi-NIC / multi-IP)
    interfaces: Mapped[list["NetworkInterface"]] = relationship(
        "NetworkInterface",
        back_populates="asset",
        cascade="all, delete-orphan",
        foreign_keys="NetworkInterface.asset_id",
    )

    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('physical', 'virtual', 'network_device', 'other', "
            "'cloud_server', 'storage', 'security_device', 'load_balancer')",
            name="ck_assets_type",
        ),
        CheckConstraint(
            "importance IN ('core', 'important', 'normal')",
            name="ck_assets_importance",
        ),
        CheckConstraint(
            "network_zone IN ('dmz', 'intranet', 'office', 'management', 'other', "
            "'aliyun', 'tencent', 'huawei', 'aws', 'azure', 'gcp', 'other_cloud')",
            name="ck_assets_zone",
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'decommissioned')",
            name="ck_assets_status",
        ),
        CheckConstraint(
            "source IN ('scan', 'manual', 'excel')",
            name="ck_assets_source",
        ),
        Index("idx_assets_ip", "ip_address"),
        Index("idx_assets_mac", "mac_address"),
        Index("idx_assets_zone", "network_zone"),
        Index("idx_assets_status", "status"),
        Index("idx_assets_serial", "serial_number"),
        Index("idx_assets_cloud_instance", "cloud_instance_id"),
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} asset_no={self.asset_no} ip={self.ip_address}>"


class AssetPort(Base):
    __tablename__ = "asset_ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    port_number: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(10), nullable=False)  # tcp / udp
    service_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(20), nullable=True)  # open/closed/filtered
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Associated asset
    asset: Mapped["Asset"] = relationship("Asset", back_populates="ports")

    __table_args__ = (
        UniqueConstraint("asset_id", "port_number", "protocol", name="uq_asset_port_proto"),
        Index("idx_ports_asset", "asset_id"),
        Index("idx_ports_number", "port_number"),
    )

    def __repr__(self) -> str:
        return f"<AssetPort asset_id={self.asset_id} {self.port_number}/{self.protocol}>"


class NetworkInterface(Base):
    """
    P0: network interface / address record.

    One row per (interface, address). Multi-NIC hosts have multiple rows;
    an interface with several IP addresses also has multiple rows (same
    name/mac, different ip_address). Bond slaves point at their master via
    bond_master. The legacy Asset.ip_address / mac_address columns stay the
    primary/management identity; this table is the detailed inventory.
    """
    __tablename__ = "network_interfaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )

    # Interface identity
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)   # eth0 / ens192 / bond0
    mac_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    cidr_prefix: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Role and bond topology
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="data")
    bond_master: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # P0/facility: port-level upstream connection (switch device + switch port)
    connected_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    connected_port: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Associated asset
    asset: Mapped["Asset"] = relationship(
        "Asset", back_populates="interfaces", foreign_keys=[asset_id]
    )

    __table_args__ = (
        CheckConstraint("role IN ('data', 'mgmt', 'other')", name="ck_nic_role"),
        CheckConstraint(
            "status IN ('active', 'disconnected')", name="ck_nic_status"
        ),
        Index("idx_nic_asset", "asset_id"),
        Index("idx_nic_ip", "ip_address"),
        Index("idx_nic_mac", "mac_address"),
        Index("idx_nic_connected", "connected_asset_id"),
    )

    def __repr__(self) -> str:
        return (f"<NetworkInterface asset_id={self.asset_id} name={self.name} "
                f"ip={self.ip_address}>")
