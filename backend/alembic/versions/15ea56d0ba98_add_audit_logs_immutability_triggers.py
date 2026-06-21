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
    # Add SQLite triggers to forbid UPDATE and DELETE on audit_logs table
    # PRD 6.2 requirement: logs can only be inserted, never modified or deleted
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS audit_logs_no_update
        BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'Audit logs cannot be modified');
        END;
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete
        BEFORE DELETE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'Audit logs cannot be deleted');
        END;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update;")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete;")
