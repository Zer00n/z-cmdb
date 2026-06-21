# Import all SQLAlchemy models in one place to ensure the mapper registry is complete.
# This prevents relationship string references (e.g. "AssetApp") from failing at init time.
from app.models.user import User
from app.models.asset import Asset, AssetPort
from app.models.asset_app import AssetApp
from app.models.audit import AuditLog
from app.models.config import SystemConfig
from app.models.llm_log import LlmCallLog
from app.models.scan import ScanBatch, ScanSnapshotItem
from app.models.topology import Topology
from app.models.cost import (
    Department, AssetCostItem, AssetRelation, AssetDeptAssignment, CostRate,
)

__all__ = [
    "User",
    "Asset",
    "AssetPort",
    "AssetApp",
    "AuditLog",
    "SystemConfig",
    "LlmCallLog",
    "ScanBatch",
    "ScanSnapshotItem",
    "Topology",
    "Department",
    "AssetCostItem",
    "AssetRelation",
    "AssetDeptAssignment",
    "CostRate",
]
