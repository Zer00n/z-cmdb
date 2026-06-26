"""
Scan batch + snapshot item SQLAlchemy model
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now


class ScanBatch(Base):
    __tablename__ = "scan_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    scan_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scan_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_hosts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="scan")

    # Associated snapshot items
    items: Mapped[list["ScanSnapshotItem"]] = relationship(
        "ScanSnapshotItem", back_populates="batch", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ScanBatch id={self.id} status={self.status}>"


class ScanSnapshotItem(Base):
    __tablename__ = "scan_snapshot_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scan_batches.id", ondelete="CASCADE"), nullable=False
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    matched_asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    diff_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Associated batch
    batch: Mapped["ScanBatch"] = relationship("ScanBatch", back_populates="items")

    def __repr__(self) -> str:
        return f"<ScanSnapshotItem batch={self.scan_batch_id} ip={self.ip_address}>"
