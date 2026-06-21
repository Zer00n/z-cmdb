# 统一导入所有 SQLAlchemy 模型，确保 mapper registry 完整
# 避免 relationship 字符串引用（如 "AssetApp"）在初始化时找不到目标类
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
