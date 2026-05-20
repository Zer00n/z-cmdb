"""
资产 SQLAlchemy 模型
"""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 业务主键
    asset_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # 网络标识
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    mac_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 分类
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    os_info: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 位置与归属
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    business_system: Mapped[str] = mapped_column(String(100), nullable=False)

    # 重要性与区域
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    network_zone: Mapped[str] = mapped_column(String(20), nullable=False)

    # 硬件信息（可选）
    cpu: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 采购信息（可选）
    purchase_date: Mapped[str | None] = mapped_column(String(20), nullable=True)   # ISO date string
    warranty_expiry: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 备注
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 状态与来源
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    # 扫描相关（系统维护）
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scan_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # 关联端口
    ports: Mapped[list["AssetPort"]] = relationship(
        "AssetPort", back_populates="asset", cascade="all, delete-orphan"
    )

    # 关联应用（v2.5）
    apps: Mapped[list["AssetApp"]] = relationship(
        "AssetApp", back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('physical', 'virtual', 'network_device', 'other')",
            name="ck_assets_type",
        ),
        CheckConstraint(
            "importance IN ('core', 'important', 'normal')",
            name="ck_assets_importance",
        ),
        CheckConstraint(
            "network_zone IN ('dmz', 'intranet', 'office', 'management', 'other')",
            name="ck_assets_zone",
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'decommissioned')",
            name="ck_assets_status",
        ),
        CheckConstraint(
            "source IN ('scan', 'manual')",
            name="ck_assets_source",
        ),
        Index("idx_assets_ip", "ip_address"),
        Index("idx_assets_mac", "mac_address"),
        Index("idx_assets_zone", "network_zone"),
        Index("idx_assets_status", "status"),
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

    # 关联资产
    asset: Mapped["Asset"] = relationship("Asset", back_populates="ports")

    __table_args__ = (
        UniqueConstraint("asset_id", "port_number", "protocol", name="uq_asset_port_proto"),
        Index("idx_ports_asset", "asset_id"),
        Index("idx_ports_number", "port_number"),
    )

    def __repr__(self) -> str:
        return f"<AssetPort asset_id={self.asset_id} {self.port_number}/{self.protocol}>"
