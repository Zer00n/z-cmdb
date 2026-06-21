"""add cost accounting tables (V0.4)

Revision ID: b4c5d6e7f8a9
Revises: f3a8c2d1e9b7
Create Date: 2026-06-21 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "f3a8c2d1e9b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create departments table ──────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # ── 2. Create asset_cost_items table ────────────────────────
    op.create_table(
        "asset_cost_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cost_type", sa.String(32), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="CNY"),
        sa.Column("billing_cycle", sa.String(20), nullable=False, server_default="month"),
        sa.Column("effective_from", sa.String(20), nullable=True),
        sa.Column("effective_to", sa.String(20), nullable=True),
        sa.Column("tax_included", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "cost_type IN ('depreciation', 'maintenance', 'power', 'hosting', "
            "'license', 'cloud_subscription', 'allocation')",
            name="ck_cost_item_type",
        ),
        sa.CheckConstraint(
            "billing_cycle IN ('once', 'month', 'quarter', 'year')",
            name="ck_cost_item_cycle",
        ),
    )
    op.create_index("idx_cost_items_asset", "asset_cost_items", ["asset_id"])

    # ── 3. Create asset_relations table ─────────────────────────
    op.create_table(
        "asset_relations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(32), nullable=False),
        sa.Column("driver_type", sa.String(32), nullable=False, server_default="even"),
        sa.Column("driver_value", sa.Float(), nullable=True),
        sa.Column("effective_from", sa.String(20), nullable=True),
        sa.Column("effective_to", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "relation_type IN ('runs_on', 'uses_storage', 'protected_by', "
            "'connected_to', 'balanced_by')",
            name="ck_relation_type",
        ),
        sa.CheckConstraint(
            "driver_type IN ('percent', 'gb', 'vcpu_weight', 'protected_count', "
            "'port_count', 'even')",
            name="ck_driver_type",
        ),
    )
    op.create_index("idx_relations_source", "asset_relations", ["source_asset_id"])
    op.create_index("idx_relations_target", "asset_relations", ["target_asset_id"])

    # ── 4. Create asset_dept_assignments table ──────────────────
    op.create_table(
        "asset_dept_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dept_id", sa.Integer(), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("billing_mode", sa.String(20), nullable=False, server_default="cost"),
        sa.Column("share_or_usage", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.String(20), nullable=False),
        sa.Column("effective_to", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "billing_mode IN ('cost', 'unit_price')",
            name="ck_billing_mode",
        ),
    )
    op.create_index("idx_dept_assign_asset", "asset_dept_assignments", ["asset_id"])
    op.create_index("idx_dept_assign_dept", "asset_dept_assignments", ["dept_id"])

    # ── 5. Create cost_rates table ──────────────────────────────
    op.create_table(
        "cost_rates",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
    )

    # ── 6. Extend assets table (add cost columns) ──────────────
    # SQLite: use batch_alter_table to rebuild the table with new columns and constraints
    with op.batch_alter_table("assets", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("purchase_price", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("depreciation_months", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("residual_rate", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("depreciation_method", sa.String(20), nullable=True, server_default="straight_line"))
        batch_op.add_column(sa.Column("end_of_life_strategy", sa.String(20), nullable=True, server_default="zero"))
        batch_op.add_column(sa.Column("revalue_amount", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("revalue_months", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("revalue_effective_date", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("billing_mode", sa.String(20), nullable=True, server_default="cost"))
        batch_op.add_column(sa.Column("responsible_dept_id", sa.Integer(), nullable=True))
        # Rebuild all existing constraints
        batch_op.create_check_constraint(
            "ck_assets_type",
            "asset_type IN ('physical', 'virtual', 'network_device', 'other', 'cloud_server')",
        )
        batch_op.create_check_constraint(
            "ck_assets_importance",
            "importance IN ('core', 'important', 'normal')",
        )
        batch_op.create_check_constraint(
            "ck_assets_zone",
            "network_zone IN ('dmz', 'intranet', 'office', 'management', 'other', "
            "'aliyun', 'tencent', 'huawei', 'aws', 'azure', 'gcp', 'other_cloud')",
        )
        batch_op.create_check_constraint(
            "ck_assets_status",
            "status IN ('online', 'offline', 'decommissioned')",
        )
        batch_op.create_check_constraint(
            "ck_assets_source",
            "source IN ('scan', 'manual')",
        )
        batch_op.create_check_constraint(
            "ck_assets_depr_method",
            "depreciation_method IS NULL OR depreciation_method IN ('straight_line', 'accelerated')",
        )
        batch_op.create_check_constraint(
            "ck_assets_eol_strategy",
            "end_of_life_strategy IS NULL OR end_of_life_strategy IN ('zero', 'revalue')",
        )
        batch_op.create_check_constraint(
            "ck_assets_billing_mode",
            "billing_mode IS NULL OR billing_mode IN ('cost', 'unit_price')",
        )


def downgrade() -> None:
    # Rebuild assets table to remove cost columns
    with op.batch_alter_table("assets", recreate="always") as batch_op:
        batch_op.drop_column("responsible_dept_id")
        batch_op.drop_column("billing_mode")
        batch_op.drop_column("revalue_effective_date")
        batch_op.drop_column("revalue_months")
        batch_op.drop_column("revalue_amount")
        batch_op.drop_column("end_of_life_strategy")
        batch_op.drop_column("depreciation_method")
        batch_op.drop_column("residual_rate")
        batch_op.drop_column("depreciation_months")
        batch_op.drop_column("purchase_price")
        # Rebuild original constraints
        batch_op.create_check_constraint(
            "ck_assets_type",
            "asset_type IN ('physical', 'virtual', 'network_device', 'other', 'cloud_server')",
        )
        batch_op.create_check_constraint(
            "ck_assets_importance",
            "importance IN ('core', 'important', 'normal')",
        )
        batch_op.create_check_constraint(
            "ck_assets_zone",
            "network_zone IN ('dmz', 'intranet', 'office', 'management', 'other', "
            "'aliyun', 'tencent', 'huawei', 'aws', 'azure', 'gcp', 'other_cloud')",
        )
        batch_op.create_check_constraint(
            "ck_assets_status",
            "status IN ('online', 'offline', 'decommissioned')",
        )
        batch_op.create_check_constraint(
            "ck_assets_source",
            "source IN ('scan', 'manual')",
        )

    op.drop_table("cost_rates")
    op.drop_index("idx_dept_assign_dept", table_name="asset_dept_assignments")
    op.drop_index("idx_dept_assign_asset", table_name="asset_dept_assignments")
    op.drop_table("asset_dept_assignments")
    op.drop_index("idx_relations_target", table_name="asset_relations")
    op.drop_index("idx_relations_source", table_name="asset_relations")
    op.drop_table("asset_relations")
    op.drop_index("idx_cost_items_asset", table_name="asset_cost_items")
    op.drop_table("asset_cost_items")
    op.drop_table("departments")
