"""
Alembic migration environment configuration
Reads database URL from app config, supports autogenerate
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

# Override sqlalchemy.url from alembic.ini
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
