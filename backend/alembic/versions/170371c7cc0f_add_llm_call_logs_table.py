"""add_llm_call_logs_table

Revision ID: 170371c7cc0f
Revises: 15ea56d0ba98
Create Date: 2026-05-20 14:19:16.333797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '170371c7cc0f'
down_revision: Union[str, None] = '15ea56d0ba98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('llm_call_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('purpose', sa.String(length=100), nullable=True),
        sa.Column('sanitized_request', sa.Text(), nullable=True),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('elapsed_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('llm_call_logs')
