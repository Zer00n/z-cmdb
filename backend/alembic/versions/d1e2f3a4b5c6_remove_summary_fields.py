"""remove AI summary cache columns from project

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-06-25

Removes 4 nullable columns (summary_overview, summary_risk, summary_lang,
summary_generated_at) from the project table.  AI project summary feature
has been removed from the product.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("project", "summary_generated_at")
    op.drop_column("project", "summary_lang")
    op.drop_column("project", "summary_risk")
    op.drop_column("project", "summary_overview")


def downgrade() -> None:
    op.add_column("project", sa.Column("summary_overview", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("summary_risk", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("summary_lang", sa.String(5), nullable=True))
    op.add_column("project", sa.Column("summary_generated_at", sa.DateTime(), nullable=True))
