"""V0.6 consuming unit model"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utc_now


class ConsumingUnit(Base):
    __tablename__ = "consuming_unit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("project.id", ondelete="SET NULL"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "type IN ('k8s_workload', 'docker', 'vm_app', 'host_process')",
            name="ck_consuming_unit_type",
        ),
        CheckConstraint(
            "environment IS NULL OR environment IN ('prod', 'staging', 'dev')",
            name="ck_consuming_unit_env",
        ),
    )

    def __repr__(self) -> str:
        return f"<ConsumingUnit id={self.id} name={self.name} project_id={self.project_id}>"
