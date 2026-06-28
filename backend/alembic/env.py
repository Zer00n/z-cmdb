"""
Alembic migration environment configuration

加密模型（PRD §6）：迁移必须在解锁/setup 之后执行 —— 此时 keyvault 持有运行态
DEK，database.get_engine() 返回已 key 的加密引擎。本 env.py 从 keyvault 取 DEK
并复用该引擎跑迁移；**无 DEK（LOCKED）时直接报错退出，禁止在无 key 状态迁移**。

注意：原先从 settings.DATABASE_URL 直接构造明文引擎的方式在加密模型下不成立
（会以「file is not a database」失败），故 online 迁移一律走已 key 引擎。
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add backend/ to sys.path so the app package can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import Base  # noqa: F401 — importing Base activates model registration

# Import all models so that Base.metadata contains all tables (required for autogenerate)
from app.models.user import User  # noqa: F401
from app.models.asset import Asset, AssetPort  # noqa: F401
from app.models.scan import ScanBatch, ScanSnapshotItem  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.config import SystemConfig  # noqa: F401
from app.models.topology import Topology  # noqa: F401
from app.models.llm_log import LlmCallLog  # noqa: F401
from app.models.asset_app import AssetApp  # noqa: F401
from app.models.cost import Department, AssetCostItem, AssetRelation, AssetDeptAssignment, CostRate  # noqa: F401
# V0.6 project-perspective models
from app.models.project import Project  # noqa: F401
from app.models.host_resource import HostResource  # noqa: F401
from app.models.consuming_unit import ConsumingUnit  # noqa: F401
from app.models.placement import Placement  # noqa: F401
from app.models.unit_relation import UnitRelation  # noqa: F401
from app.models.billing_policy import BillingPolicy  # noqa: F401
from app.models.bill_snapshot import BillSnapshot  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline 模式（仅生成 SQL 脚本，不连库）——加密模型下保留为生成 DDL 用途。

    不需要 DEK（不实际连库），但仍以 settings.DATABASE_URL 的 dialect 推导。
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online 迁移：必须用已 key 的加密引擎（PRD §6）。

    优先复用 ``database.get_engine()``（setup/unlock 流程中 init_engine 已建好）；
    若引擎尚未建（纯 alembic 命令行场景），则从 keyvault 取运行态 DEK 自建。
    二者皆不可得（LOCKED 态、无 DEK）则报错退出 —— 禁止在无 key 状态迁移。
    """
    from app.core import database, keyvault

    connectable = database.get_engine()
    if connectable is None:
        dek_hex = keyvault.get_dek_hex()
        if not dek_hex:
            raise RuntimeError(
                "Cannot run migrations: vault is LOCKED (no DEK in memory). "
                "Unlock or run setup first — migrations are deferred to after unlock (PRD §6)."
            )
        connectable = database.init_engine(dek_hex)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
