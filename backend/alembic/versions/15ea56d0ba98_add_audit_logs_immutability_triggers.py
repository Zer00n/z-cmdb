"""add_audit_logs_immutability_triggers

Revision ID: 15ea56d0ba98
Revises: 0a50eab52414
Create Date: 2026-05-20 14:00:30.471399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15ea56d0ba98'
down_revision: Union[str, None] = '0a50eab52414'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 SQLite 触发器：禁止 UPDATE 和 DELETE audit_logs 表
    # PRD 6.2 要求：日志只能新增，不能修改、不能删除
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS audit_logs_no_update
        BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, '审计日志不可修改');
        END;
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete
        BEFORE DELETE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, '审计日志不可删除');
        END;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update;")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete;")
