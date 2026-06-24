"""V0.6 bill snapshot model (frozen per period)"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utc_now


class BillSnapshot(Base):
    __tablename__ = "bill_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False,
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    frozen: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("frozen = 1", name="ck_bill_frozen_always_true"),
        UniqueConstraint("project_id", "period", name="uq_bill_project_period"),
    )

    def __repr__(self) -> str:
        return f"<BillSnapshot project_id={self.project_id} period={self.period} cost={self.total_cost}>"
