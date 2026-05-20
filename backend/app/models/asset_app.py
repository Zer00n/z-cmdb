"""
应用服务清单 SQLAlchemy 模型
v2.5: 记录资产上安装的应用/服务
"""
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now


class AssetApp(Base):
    __tablename__ = "asset_apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )

    # 应用基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(10), nullable=True)  # tcp / udp

    # 元信息
    install_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 来源与生命周期
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # 创建人
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # 关联资产
    asset: Mapped["Asset"] = relationship("Asset", back_populates="apps")

    __table_args__ = (
        UniqueConstraint("asset_id", "name", "version", name="uq_asset_app_name_version"),
        Index("idx_asset_apps_asset_id", "asset_id"),
        Index("idx_asset_apps_name", "name"),
        Index("idx_asset_apps_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<AssetApp id={self.id} asset_id={self.asset_id} name={self.name} version={self.version}>"
