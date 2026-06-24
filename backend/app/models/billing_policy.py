"""V0.6 billing policy model (versioned)"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utc_now


class BillingPolicy(Base):
    __tablename__ = "billing_policy"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    denominator: Mapped[str] = mapped_column(String(32), nullable=False)
    weight_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    weight_cpu: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    weight_mem: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    idle_cost: Mapped[str] = mapped_column(String(32), nullable=False)
    sampling: Mapped[str] = mapped_column(String(32), nullable=False)
    freeze: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "denominator IN ('allocatable', 'sum_requests')",
            name="ck_billing_denominator",
        ),
        CheckConstraint(
            "weight_mode IN ('mem', 'cpu', 'weighted', 'max')",
            name="ck_billing_weight_mode",
        ),
        CheckConstraint(
            "idle_cost IN ('unallocated_bucket', 'force_allocate')",
            name="ck_billing_idle_cost",
        ),
        CheckConstraint(
            "sampling IN ('daily', 'hourly')",
            name="ck_billing_sampling",
        ),
        CheckConstraint("freeze = 1", name="ck_billing_freeze_always_true"),
    )

    def __repr__(self) -> str:
        return f"<BillingPolicy id={self.id} v{self.version} active={self.is_active}>"
