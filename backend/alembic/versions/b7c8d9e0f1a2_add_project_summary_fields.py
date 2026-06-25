"""add project summary cache fields

Revision ID: b7c8d9e0f1a2
Revises: a2b3c4d5e6f7
Create Date: 2026-06-24

Adds 4 nullable columns to the project table for caching AI-generated summaries.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project", sa.Column("summary_overview", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("summary_risk", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("summary_lang", sa.String(5), nullable=True))
    op.add_column("project", sa.Column("summary_generated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "summary_generated_at")
    op.drop_column("project", "summary_lang")
    op.drop_column("project", "summary_risk")
    op.drop_column("project", "summary_overview")
