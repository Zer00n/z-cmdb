"""add P0 hardware identity, structured location, cloud fields and network interfaces

Revision ID: h5c0d4e6f2a9
Revises: g4b9c3d2e1f8
Create Date: 2026-09-22

P0 asset-platform enhancements:
- assets: add nullable hardware identity (serial/vendor/model/tag), structured
  rack location (datacenter/rack/u_start/u_height), out-of-band mgmt_ip and
  cloud/virtualization identity columns; all nullable -> legacy logic unaffected.
- assets: asset_type CHECK extended with storage / security_device / load_balancer.
- new network_interfaces table for multi-NIC / multi-IP inventory.

SQLite cannot ALTER a CHECK constraint, so the assets table is rebuilt
(batch mode) exactly as in the cloud_server migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h5c0d4e6f2a9"
down_revision: Union[str, None] = "g4b9c3d2e1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New nullable columns on assets
_NEW_COLUMNS = [
    sa.Column("serial_number", sa.String(length=128), nullable=True),
    sa.Column("vendor", sa.String(length=128), nullable=True),
    sa.Column("hardware_model", sa.String(length=128), nullable=True),
    sa.Column("asset_tag", sa.String(length=64), nullable=True),
    sa.Column("datacenter", sa.String(length=128), nullable=True),
    sa.Column("rack", sa.String(length=64), nullable=True),
    sa.Column("rack_u_start", sa.Integer(), nullable=True),
    sa.Column("rack_u_height", sa.Integer(), nullable=True),
    sa.Column("mgmt_ip", sa.String(length=45), nullable=True),
    sa.Column("cloud_instance_id", sa.String(length=128), nullable=True),
    sa.Column("cloud_region", sa.String(length=64), nullable=True),
    sa.Column("cloud_zone", sa.String(length=64), nullable=True),
    sa.Column("cloud_spec", sa.String(length=128), nullable=True),
    sa.Column("hypervisor", sa.String(length=128), nullable=True),
]

_NEW_TYPE_CHECK = (
    "asset_type IN ('physical', 'virtual', 'network_device', 'other', "
    "'cloud_server', 'storage', 'security_device', 'load_balancer')"
)
_OLD_TYPE_CHECK = (
    "asset_type IN ('physical', 'virtual', 'network_device', 'other', 'cloud_server')"
)


def upgrade() -> None:
    # Rebuild assets to add columns and update the asset_type CHECK constraint.
    with op.batch_alter_table("assets", recreate="always") as batch_op:
        for column in _NEW_COLUMNS:
            batch_op.add_column(column)
        batch_op.drop_constraint("ck_assets_type", type_="check")
        batch_op.create_check_constraint("ck_assets_type", _NEW_TYPE_CHECK)
        batch_op.create_index("idx_assets_serial", ["serial_number"])
        batch_op.create_index("idx_assets_cloud_instance", ["cloud_instance_id"])

    # Detailed network interface inventory
    op.create_table(
        "network_interfaces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=64), nullable=True),
        sa.Column("mac_address", sa.String(length=32), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("cidr_prefix", sa.Integer(), nullable=True),
        sa.Column("vlan_id", sa.Integer(), nullable=True),
        sa.Column("gateway", sa.String(length=45), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="data"),
        sa.Column("bond_master", sa.String(length=64), nullable=True),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="active"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("role IN ('data', 'mgmt', 'other')", name="ck_nic_role"),
        sa.CheckConstraint(
            "status IN ('active', 'disconnected')", name="ck_nic_status"
        ),
    )
    op.create_index("idx_nic_asset", "network_interfaces", ["asset_id"])
    op.create_index("idx_nic_ip", "network_interfaces", ["ip_address"])
    op.create_index("idx_nic_mac", "network_interfaces", ["mac_address"])


def downgrade() -> None:
    op.drop_index("idx_nic_mac", table_name="network_interfaces")
    op.drop_index("idx_nic_ip", table_name="network_interfaces")
    op.drop_index("idx_nic_asset", table_name="network_interfaces")
    op.drop_table("network_interfaces")

    with op.batch_alter_table("assets", recreate="always") as batch_op:
        batch_op.drop_index("idx_assets_cloud_instance")
        batch_op.drop_index("idx_assets_serial")
        batch_op.drop_constraint("ck_assets_type", type_="check")
        batch_op.create_check_constraint("ck_assets_type", _OLD_TYPE_CHECK)
        for column in reversed(_NEW_COLUMNS):
            batch_op.drop_column(column.name)
