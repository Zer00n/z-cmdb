"""V0.6 unit relation model (dependency edge)"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utc_now


class UnitRelation(Base):
    __tablename__ = "unit_relation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consuming_unit.id", ondelete="CASCADE"), nullable=False,
    )
    target_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("consuming_unit.id", ondelete="CASCADE"), nullable=False,
    )
    rel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "rel_type IN ('HTTP', 'SQL', 'cache', 'mq', 'depends')",
            name="ck_unit_relation_type",
        ),
        CheckConstraint(
            "source IN ('manual', 'mesh', 'apm')",
            name="ck_unit_relation_source",
        ),
    )

    def __repr__(self) -> str:
        return f"<UnitRelation id={self.id} {self.source_unit_id}->{self.target_unit_id} type={self.rel_type}>"
