"""add racks table, assets.rack_id and port-level cabling columns

Revision ID: i6d1e5f7a3b0
Revises: h5c0d4e6f2a9
Create Date: 2026-09-22

Facility / rack elevation support:
- racks table (datacenter + unique rack name, u_height default 42).
- assets.rack_id nullable FK; backfilled from distinct (datacenter, rack) text.
- network_interfaces gains connected_asset_id / connected_port for port-level
  upstream cabling. All new columns nullable -> existing logic unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i6d1e5f7a3b0"
down_revision: Union[str, None] = "h5c0d4e6f2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "racks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("datacenter", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("u_height", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("room", sa.String(length=128), nullable=True),
        sa.Column("row_label", sa.String(length=64), nullable=True),
        sa.Column("col_label", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("u_height BETWEEN 1 AND 52", name="ck_rack_u_height"),
        sa.UniqueConstraint("datacenter", "name", name="uq_rack_datacenter_name"),
    )

    # Adding an FK column on SQLite requires batch (copy) mode
    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(
            sa.Column(
                "rack_id", sa.Integer(),
                sa.ForeignKey("racks.id", ondelete="SET NULL",
                              name="fk_assets_rack_id"),
                nullable=True,
            )
        )

    # Backfill one rack per distinct (datacenter, rack) pair
    op.execute(
        """
        INSERT INTO racks (datacenter, name, u_height, created_at, updated_at)
        SELECT DISTINCT NULLIF(TRIM(datacenter), ''), TRIM(rack), 42,
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM assets
        WHERE COALESCE(TRIM(rack), '') <> ''
        """
    )

    # Link each asset to its resolved rack
    op.execute(
        """
        UPDATE assets
        SET rack_id = (
            SELECT r.id FROM racks r
            WHERE r.name = TRIM(assets.rack)
              AND (
                (r.datacenter IS NULL AND COALESCE(TRIM(assets.datacenter), '') = '')
                OR r.datacenter = TRIM(assets.datacenter)
              )
        )
        WHERE COALESCE(TRIM(rack), '') <> ''
        """
    )

    # Port-level upstream cabling columns (FK column needs batch mode on SQLite)
    with op.batch_alter_table("network_interfaces") as batch_op:
        batch_op.add_column(
            sa.Column(
                "connected_asset_id", sa.Integer(),
                sa.ForeignKey("assets.id", ondelete="SET NULL",
                              name="fk_nic_connected_asset"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("connected_port", sa.String(length=64), nullable=True)
        )
    op.create_index(
        "idx_nic_connected", "network_interfaces", ["connected_asset_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_nic_connected", table_name="network_interfaces")
    with op.batch_alter_table("network_interfaces") as batch_op:
        batch_op.drop_column("connected_port")
        batch_op.drop_column("connected_asset_id")
    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_column("rack_id")
    op.drop_table("racks")
