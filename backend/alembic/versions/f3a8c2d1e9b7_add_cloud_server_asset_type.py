"""add cloud_server asset type and cloud network zones

Revision ID: f3a8c2d1e9b7
Revises: 15ea56d0ba98
Create Date: 2026-05-22 12:00:00.000000

SQLite 不支持 DROP CONSTRAINT，通过重建表来更新 CheckConstraint。
- asset_type 新增 'cloud_server'
- network_zone 新增 'aliyun' | 'tencent' | 'huawei' | 'aws' | 'azure' | 'gcp' | 'other_cloud'
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a8c2d1e9b7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite: 重建 assets 表以更新 CheckConstraint
    with op.batch_alter_table('assets', recreate='always') as batch_op:
        batch_op.alter_column(
            'asset_type',
            existing_type=sa.String(length=32),
            type_=sa.String(length=32),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'network_zone',
            existing_type=sa.String(length=20),
            type_=sa.String(length=32),  # 扩展长度以容纳 'other_cloud'
            existing_nullable=False,
        )
        # 删除旧约束，添加新约束
        batch_op.drop_constraint('ck_assets_type', type_='check')
        batch_op.drop_constraint('ck_assets_zone', type_='check')
        batch_op.create_check_constraint(
            'ck_assets_type',
            "asset_type IN ('physical', 'virtual', 'network_device', 'other', 'cloud_server')",
        )
        batch_op.create_check_constraint(
            'ck_assets_zone',
            "network_zone IN ('dmz', 'intranet', 'office', 'management', 'other', "
            "'aliyun', 'tencent', 'huawei', 'aws', 'azure', 'gcp', 'other_cloud')",
        )


def downgrade() -> None:
    with op.batch_alter_table('assets', recreate='always') as batch_op:
        batch_op.alter_column(
            'network_zone',
            existing_type=sa.String(length=32),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
        batch_op.drop_constraint('ck_assets_type', type_='check')
        batch_op.drop_constraint('ck_assets_zone', type_='check')
        batch_op.create_check_constraint(
            'ck_assets_type',
            "asset_type IN ('physical', 'virtual', 'network_device', 'other')",
        )
        batch_op.create_check_constraint(
            'ck_assets_zone',
            "network_zone IN ('dmz', 'intranet', 'office', 'management', 'other')",
        )
