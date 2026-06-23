"""add index on scan_snapshot_items.ip_address

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-06-23

"""
from typing import Union

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, None] = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_scan_snapshot_items_ip_address", "scan_snapshot_items", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_scan_snapshot_items_ip_address", table_name="scan_snapshot_items")
