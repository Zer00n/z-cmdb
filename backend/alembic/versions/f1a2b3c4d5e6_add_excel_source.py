"""add excel source support

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-06-26

1. Add 'source' column to scan_batches (default='scan')
2. Update assets CHECK constraint to include 'excel'
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source column to scan_batches
    op.add_column(
        "scan_batches",
        sa.Column("source", sa.String(20), nullable=False, server_default="scan"),
    )

    # Update assets CHECK constraint to include 'excel'
    # SQLite requires batch_alter_table to modify constraints
    with op.batch_alter_table("assets", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_assets_source", type_="check")
        batch_op.create_check_constraint(
            "ck_assets_source",
            "source IN ('scan', 'manual', 'excel')",
        )


def downgrade() -> None:
    with op.batch_alter_table("assets", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_assets_source", type_="check")
        batch_op.create_check_constraint(
            "ck_assets_source",
            "source IN ('scan', 'manual')",
        )

    op.drop_column("scan_batches", "source")
