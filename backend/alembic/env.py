"""
Alembic 迁移环境配置
从应用配置读取数据库 URL，支持 autogenerate
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 将 backend/ 加入 sys.path，使 app 包可被导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import Base  # noqa: F401 — 导入 Base 使模型注册生效

# 导入所有模型，使 Base.metadata 包含所有表（autogenerate 需要）
from app.models.user import User  # noqa: F401
from app.models.asset import Asset, AssetPort  # noqa: F401
from app.models.scan import ScanBatch, ScanSnapshotItem  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.config import SystemConfig  # noqa: F401
from app.models.topology import Topology  # noqa: F401
from app.models.llm_log import LlmCallLog  # noqa: F401
from app.models.asset_app import AssetApp  # noqa: F401
from app.models.cost import Department, AssetCostItem, AssetRelation, AssetDeptAssignment, CostRate  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 覆盖 alembic.ini 中的 sqlalchemy.url
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
