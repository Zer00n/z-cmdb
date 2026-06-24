"""V0.6 host resource model"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utc_now


class HostResource(Base):
    __tablename__ = "host_resource"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_host_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cpu_total: Mapped[float] = mapped_column(Float, nullable=False)
    mem_total: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "type IN ('physical', 'vm', 'k8s_node')",
            name="ck_host_resource_type",
        ),
        CheckConstraint(
            "source IN ('cmdb', 'k8s', 'agent', 'manual')",
            name="ck_host_resource_source",
        ),
    )

    def __repr__(self) -> str:
        return f"<HostResource id={self.id} name={self.name} type={self.type}>"
