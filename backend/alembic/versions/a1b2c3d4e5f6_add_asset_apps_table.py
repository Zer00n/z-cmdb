"""add asset_apps table

Revision ID: a1b2c3d4e5f6
Revises: 170371c7cc0f
Create Date: 2026-05-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '170371c7cc0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('asset_apps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('protocol', sa.String(length=10), nullable=True),
        sa.Column('install_path', sa.String(length=255), nullable=True),
        sa.Column('config_path', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='manual'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'name', 'version', name='uq_asset_app_name_version'),
    )
    op.create_index('idx_asset_apps_asset_id', 'asset_apps', ['asset_id'], unique=False)
    op.create_index('idx_asset_apps_name', 'asset_apps', ['name'], unique=False)
    op.create_index('idx_asset_apps_category', 'asset_apps', ['category'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_asset_apps_category', table_name='asset_apps')
    op.drop_index('idx_asset_apps_name', table_name='asset_apps')
    op.drop_index('idx_asset_apps_asset_id', table_name='asset_apps')
    op.drop_table('asset_apps')
