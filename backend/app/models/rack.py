"""
Server rack / cabinet model (facility view)

Racks are auto-created from asset (datacenter, rack) text pairs on save and
can also be added manually for empty cabinets. u_height defaults to 42.
"""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, utc_now


class Rack(Base):
    __tablename__ = "racks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # A rack belongs to a datacenter; datacenter may be NULL when only rack is known
    datacenter: Mapped[str | None] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Total U positions of this cabinet (industry default 42)
    u_height: Mapped[int] = mapped_column(Integer, nullable=False, default=42)

    # In-room placement metadata (reserved; floor plan comes later)
    room: Mapped[str | None] = mapped_column(String(128), nullable=True)
    row_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    col_label: Mapped[str | None] = mapped_column(String(64), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("datacenter", "name", name="uq_rack_datacenter_name"),
        CheckConstraint("u_height BETWEEN 1 AND 52", name="ck_rack_u_height"),
    )

    def __repr__(self) -> str:
        return f"<Rack id={self.id} datacenter={self.datacenter} name={self.name}>"
