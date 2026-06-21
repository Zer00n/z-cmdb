"""
V0.4 成本核算相关模型
Department / AssetCostItem / AssetRelation / AssetDeptAssignment / CostRate
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utc_now


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.name}>"


class AssetCostItem(Base):
    """资产成本行：折旧/维保/电力/托管/许可/云订阅/分摊"""
    __tablename__ = "asset_cost_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    cost_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="CNY")
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="month")
    effective_from: Mapped[str | None] = mapped_column(String(20), nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "cost_type IN ('depreciation', 'maintenance', 'power', 'hosting', "
            "'license', 'cloud_subscription', 'allocation')",
            name="ck_cost_item_type",
        ),
        CheckConstraint(
            "billing_cycle IN ('once', 'month', 'quarter', 'year')",
            name="ck_cost_item_cycle",
        ),
        Index("idx_cost_items_asset", "asset_id"),
    )

    def __repr__(self) -> str:
        return f"<AssetCostItem asset_id={self.asset_id} type={self.cost_type} amount={self.amount}>"


class AssetRelation(Base):
    """资产关系：VM→宿主、资产→存储/防火墙/LB/网络设备"""
    __tablename__ = "asset_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    target_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    driver_type: Mapped[str] = mapped_column(String(32), nullable=False, default="even")
    driver_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_from: Mapped[str | None] = mapped_column(String(20), nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('runs_on', 'uses_storage', 'protected_by', "
            "'connected_to', 'balanced_by')",
            name="ck_relation_type",
        ),
        CheckConstraint(
            "driver_type IN ('percent', 'gb', 'vcpu_weight', 'protected_count', "
            "'port_count', 'even')",
            name="ck_driver_type",
        ),
        Index("idx_relations_source", "source_asset_id"),
        Index("idx_relations_target", "target_asset_id"),
    )

    def __repr__(self) -> str:
        return (f"<AssetRelation {self.source_asset_id}->{self.target_asset_id} "
                f"type={self.relation_type}>")


class AssetDeptAssignment(Base):
    """资产部门归属与计费分段"""
    __tablename__ = "asset_dept_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    dept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    billing_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="cost")
    share_or_usage: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    effective_from: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_to: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "billing_mode IN ('cost', 'unit_price')",
            name="ck_billing_mode",
        ),
        Index("idx_dept_assign_asset", "asset_id"),
        Index("idx_dept_assign_dept", "dept_id"),
    )

    def __repr__(self) -> str:
        return (f"<AssetDeptAssignment asset={self.asset_id} dept={self.dept_id} "
                f"mode={self.billing_mode}>")


class CostRate(Base):
    """费率字典（KV 存 JSON）"""
    __tablename__ = "cost_rates"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<CostRate key={self.key}>"
