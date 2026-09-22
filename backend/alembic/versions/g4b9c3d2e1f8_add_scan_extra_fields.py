"""add extra_fields_json to scan_batches

Revision ID: g4b9c3d2e1f8
Revises: f1a2b3c4d5e6
Create Date: 2026-09-22

Excel 导入的补充字段改存数据库列，替代历史明文 JSON 边车文件（安全审计 V7）。
只加可空列，旧代码可安全忽略。
"""
from alembic import op
import sqlalchemy as sa

revision = "g4b9c3d2e1f8"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scan_batches",
        sa.Column("extra_fields_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_batches", "extra_fields_json")
