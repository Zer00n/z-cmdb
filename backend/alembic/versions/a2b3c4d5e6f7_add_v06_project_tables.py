"""add v0.6 project-perspective tables

Revision ID: a2b3c4d5e6f7
Revises: f0a1b2c3d4e5
Create Date: 2026-06-24

Creates 7 new tables for the project-perspective and consumption-driven billing:
  project, host_resource, consuming_unit, placement, unit_relation,
  billing_policy, bill_snapshot

Also inserts the default billing policy (v1, allocatable + mem).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. project ──────────────────────────────────────────────
    op.create_table(
        "project",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("business_unit", sa.String(100), nullable=True),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("billing_enabled", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── 2. host_resource ────────────────────────────────────────
    op.create_table(
        "host_resource",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("parent_host_id", sa.String(36), nullable=True),
        sa.Column("cpu_total", sa.Float, nullable=False),
        sa.Column("mem_total", sa.Float, nullable=False),
        sa.Column("monthly_cost", sa.Float, nullable=False, server_default="0"),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('physical', 'vm', 'k8s_node')",
            name="ck_host_resource_type",
        ),
        sa.CheckConstraint(
            "source IN ('cmdb', 'k8s', 'agent', 'manual')",
            name="ck_host_resource_source",
        ),
    )

    # ── 3. consuming_unit ───────────────────────────────────────
    op.create_table(
        "consuming_unit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("project.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("environment", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "type IN ('k8s_workload', 'docker', 'vm_app', 'host_process')",
            name="ck_consuming_unit_type",
        ),
        sa.CheckConstraint(
            "environment IS NULL OR environment IN ('prod', 'staging', 'dev')",
            name="ck_consuming_unit_env",
        ),
    )

    # ── 4. placement (read-only, time-variant) ──────────────────
    op.create_table(
        "placement",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("unit_id", sa.String(36), sa.ForeignKey("consuming_unit.id", ondelete="CASCADE"), nullable=False),
        sa.Column("host_id", sa.String(36), sa.ForeignKey("host_resource.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cpu_request", sa.Float, nullable=False),
        sa.Column("mem_request", sa.Float, nullable=False),
        sa.Column("instances", sa.Integer, nullable=False, server_default="1"),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("observed_at", sa.String(30), nullable=False),
        sa.CheckConstraint(
            "source IN ('k8s', 'agent', 'manual')",
            name="ck_placement_source",
        ),
    )
    op.create_index("idx_placement_unit", "placement", ["unit_id", "observed_at"])
    op.create_index("idx_placement_host", "placement", ["host_id", "observed_at"])

    # ── 5. unit_relation (dependency edge) ──────────────────────
    op.create_table(
        "unit_relation",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_unit_id", sa.String(36), sa.ForeignKey("consuming_unit.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_unit_id", sa.String(36), sa.ForeignKey("consuming_unit.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rel_type", sa.String(32), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "rel_type IN ('HTTP', 'SQL', 'cache', 'mq', 'depends')",
            name="ck_unit_relation_type",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'mesh', 'apm')",
            name="ck_unit_relation_source",
        ),
    )

    # ── 6. billing_policy (versioned) ───────────────────────────
    op.create_table(
        "billing_policy",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("denominator", sa.String(32), nullable=False),
        sa.Column("weight_mode", sa.String(32), nullable=False),
        sa.Column("weight_cpu", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("weight_mem", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("idle_cost", sa.String(32), nullable=False),
        sa.Column("sampling", sa.String(32), nullable=False),
        sa.Column("freeze", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "denominator IN ('allocatable', 'sum_requests')",
            name="ck_billing_denominator",
        ),
        sa.CheckConstraint(
            "weight_mode IN ('mem', 'cpu', 'weighted', 'max')",
            name="ck_billing_weight_mode",
        ),
        sa.CheckConstraint(
            "idle_cost IN ('unallocated_bucket', 'force_allocate')",
            name="ck_billing_idle_cost",
        ),
        sa.CheckConstraint(
            "sampling IN ('daily', 'hourly')",
            name="ck_billing_sampling",
        ),
        sa.CheckConstraint("freeze = 1", name="ck_billing_freeze_always_true"),
    )

    # Insert default billing policy (v0.6 factory default, locked)
    op.execute(
        """INSERT INTO billing_policy
           (id, version, denominator, weight_mode, weight_cpu, weight_mem,
            idle_cost, sampling, freeze, is_active, created_at)
           VALUES
           ('default-policy-v1', 1, 'allocatable', 'mem', 0.5, 0.5,
            'unallocated_bucket', 'daily', 1, 1, datetime('now'))"""
    )

    # ── 7. bill_snapshot (frozen per period) ────────────────────
    op.create_table(
        "bill_snapshot",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("policy_version", sa.Integer, nullable=False),
        sa.Column("total_cost", sa.Float, nullable=False),
        sa.Column("detail_json", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("frozen", sa.Integer, nullable=False, server_default="1"),
        sa.CheckConstraint("frozen = 1", name="ck_bill_frozen_always_true"),
        sa.UniqueConstraint("project_id", "period", name="uq_bill_project_period"),
    )
    op.create_index("idx_bill_project_period", "bill_snapshot", ["project_id", "period"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("idx_bill_project_period", table_name="bill_snapshot")
    op.drop_table("bill_snapshot")
    op.drop_table("billing_policy")
    op.drop_table("unit_relation")
    op.drop_index("idx_placement_host", table_name="placement")
    op.drop_index("idx_placement_unit", table_name="placement")
    op.drop_table("placement")
    op.drop_table("consuming_unit")
    op.drop_table("host_resource")
    op.drop_table("project")
