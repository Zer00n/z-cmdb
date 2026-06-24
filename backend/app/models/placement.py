"""V0.6 placement model (read-only, time-variant)"""
import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Placement(Base):
    __tablename__ = "placement"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consuming_unit.id", ondelete="CASCADE"), nullable=False,
    )
    host_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("host_resource.id", ondelete="CASCADE"), nullable=False,
    )
    cpu_request: Mapped[float] = mapped_column(Float, nullable=False)
    mem_request: Mapped[float] = mapped_column(Float, nullable=False)
    instances: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_at: Mapped[str] = mapped_column(String(30), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "source IN ('k8s', 'agent', 'manual')",
            name="ck_placement_source",
        ),
        Index("idx_placement_unit", "unit_id", "observed_at"),
        Index("idx_placement_host", "host_id", "observed_at"),
    )

    def __repr__(self) -> str:
        return f"<Placement id={self.id} unit_id={self.unit_id} host_id={self.host_id}>"
