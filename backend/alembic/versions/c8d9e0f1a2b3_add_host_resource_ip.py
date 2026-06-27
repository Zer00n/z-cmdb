"""add ip_address to host_resource

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-06-24

Adds a nullable ip_address column to host_resource for IP-based host lookup.
Also backfills ip_address from the asset table where hostname matches host_resource.name.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("host_resource", sa.Column("ip_address", sa.String(45), nullable=True))

    # Backfill: copy ip_address from asset where hostname = host_resource.name
    # Skip if asset table doesn't exist (fresh deployment without V0.1-V0.4 data)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "asset" in inspector.get_table_names():
        conn.execute(
            sa.text(
                """
                UPDATE host_resource
                SET ip_address = (
                    SELECT a.ip_address
                    FROM asset a
                    WHERE a.hostname = host_resource.name
                      AND a.ip_address IS NOT NULL
                      AND a.ip_address != ''
                    LIMIT 1
                )
                WHERE ip_address IS NULL
                  AND EXISTS (
                    SELECT 1 FROM asset a
                    WHERE a.hostname = host_resource.name
                  )
                """
            )
        )


def downgrade() -> None:
    op.drop_column("host_resource", "ip_address")
