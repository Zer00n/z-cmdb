"""
成本核算数据访问层
Department / AssetCostItem / AssetRelation / AssetDeptAssignment / CostRate
"""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.asset import Asset
from app.models.cost import (
    AssetCostItem,
    AssetDeptAssignment,
    AssetRelation,
    CostRate,
    Department,
)

logger = logging.getLogger(__name__)


# ── Department ─────────────────────────────────────────────────


def get_departments(db: Session) -> list[Department]:
    """列出所有部门"""
    return list(db.scalars(select(Department).order_by(Department.id)).all())


def get_department(db: Session, dept_id: int) -> Department:
    """按 id 获取单个部门"""
    dept = db.get(Department, dept_id)
    if dept is None:
        raise NotFoundError(f"部门 ID {dept_id} 不存在")
    return dept


def create_department(db: Session, name: str, code: str) -> Department:
    """创建部门"""
    dept = Department(name=name, code=code)
    db.add(dept)
    db.flush()
    logger.info("department created", extra={"dept_id": dept.id, "dept_name": name})
    return dept


def update_department(db: Session, dept_id: int, name: str, code: str) -> Department:
    """更新部门"""
    dept = get_department(db, dept_id)
    dept.name = name
    dept.code = code
    db.flush()
    logger.info("department updated", extra={"dept_id": dept_id})
    return dept


def delete_department(db: Session, dept_id: int) -> None:
    """删除部门"""
    dept = get_department(db, dept_id)
    db.delete(dept)
    db.flush()
    logger.info("department deleted", extra={"dept_id": dept_id})


# ── AssetCostItem ──────────────────────────────────────────────


def get_cost_items(db: Session, asset_id: int) -> list[AssetCostItem]:
    """列出资产的所有成本行"""
    stmt = (
        select(AssetCostItem)
        .where(AssetCostItem.asset_id == asset_id)
        .order_by(AssetCostItem.id)
    )
    return list(db.scalars(stmt).all())


def create_cost_item(db: Session, asset_id: int, **kwargs) -> AssetCostItem:
    """创建成本行"""
    item = AssetCostItem(asset_id=asset_id, **kwargs)
    db.add(item)
    db.flush()
    logger.info("cost item created", extra={"item_id": item.id, "asset_id": asset_id})
    return item


def update_cost_item(db: Session, item_id: int, **kwargs) -> AssetCostItem:
    """更新成本行"""
    item = db.get(AssetCostItem, item_id)
    if item is None:
        raise NotFoundError(f"成本行 ID {item_id} 不存在")
    for key, value in kwargs.items():
        if hasattr(item, key) and value is not None:
            setattr(item, key, value)
    db.flush()
    logger.info("cost item updated", extra={"item_id": item_id})
    return item


def delete_cost_item(db: Session, item_id: int) -> None:
    """删除成本行"""
    item = db.get(AssetCostItem, item_id)
    if item is None:
        raise NotFoundError(f"成本行 ID {item_id} 不存在")
    db.delete(item)
    db.flush()
    logger.info("cost item deleted", extra={"item_id": item_id})


# ── AssetRelation ──────────────────────────────────────────────


def get_relations(db: Session, asset_id: int) -> list[AssetRelation]:
    """列出资产的所有关系（作为 source 或 target）"""
    stmt = (
        select(AssetRelation)
        .where(
            or_(
                AssetRelation.source_asset_id == asset_id,
                AssetRelation.target_asset_id == asset_id,
            )
        )
        .order_by(AssetRelation.id)
    )
    return list(db.scalars(stmt).all())


def create_relation(db: Session, **kwargs) -> AssetRelation:
    """创建资产关系"""
    relation = AssetRelation(**kwargs)
    db.add(relation)
    db.flush()
    logger.info(
        "asset relation created",
        extra={
            "relation_id": relation.id,
            "source": relation.source_asset_id,
            "target": relation.target_asset_id,
        },
    )
    return relation


def delete_relation(db: Session, relation_id: int) -> None:
    """删除资产关系"""
    relation = db.get(AssetRelation, relation_id)
    if relation is None:
        raise NotFoundError(f"资产关系 ID {relation_id} 不存在")
    db.delete(relation)
    db.flush()
    logger.info("asset relation deleted", extra={"relation_id": relation_id})


# ── AssetDeptAssignment ────────────────────────────────────────


def get_dept_assignments(db: Session, asset_id: int) -> list[AssetDeptAssignment]:
    """列出资产的所有部门归属记录"""
    stmt = (
        select(AssetDeptAssignment)
        .where(AssetDeptAssignment.asset_id == asset_id)
        .order_by(AssetDeptAssignment.id)
    )
    return list(db.scalars(stmt).all())


def get_dept_assignments_by_dept(db: Session, dept_id: int) -> list[AssetDeptAssignment]:
    """列出部门的所有资产归属记录"""
    stmt = (
        select(AssetDeptAssignment)
        .where(AssetDeptAssignment.dept_id == dept_id)
        .order_by(AssetDeptAssignment.id)
    )
    return list(db.scalars(stmt).all())


def create_dept_assignment(db: Session, **kwargs) -> AssetDeptAssignment:
    """创建资产部门归属"""
    assignment = AssetDeptAssignment(**kwargs)
    db.add(assignment)
    db.flush()
    logger.info(
        "dept assignment created",
        extra={"assignment_id": assignment.id, "asset_id": assignment.asset_id, "dept_id": assignment.dept_id},
    )
    return assignment


def close_dept_assignment(db: Session, assignment_id: int, effective_to: str) -> AssetDeptAssignment:
    """关闭资产部门归属（设置 effective_to）"""
    assignment = db.get(AssetDeptAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError(f"部门归属 ID {assignment_id} 不存在")
    assignment.effective_to = effective_to
    db.flush()
    logger.info("dept assignment closed", extra={"assignment_id": assignment_id, "effective_to": effective_to})
    return assignment


def delete_dept_assignment(db: Session, assignment_id: int) -> None:
    """删除资产部门归属"""
    assignment = db.get(AssetDeptAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError(f"部门归属 ID {assignment_id} 不存在")
    db.delete(assignment)
    db.flush()
    logger.info("dept assignment deleted", extra={"assignment_id": assignment_id})


# ── CostRate ───────────────────────────────────────────────────


def get_all_cost_rates(db: Session) -> list[CostRate]:
    """列出所有费率"""
    return list(db.scalars(select(CostRate).order_by(CostRate.key)).all())


def get_cost_rate(db: Session, key: str) -> CostRate:
    """按 key 获取单条费率"""
    rate = db.get(CostRate, key)
    if rate is None:
        raise NotFoundError(f"费率 {key} 不存在")
    return rate


def upsert_cost_rate(
    db: Session,
    key: str,
    value,
    description: str | None = None,
    updated_by: int | None = None,
) -> CostRate:
    """创建或更新费率"""
    rate = db.get(CostRate, key)
    if rate is None:
        rate = CostRate(key=key)
        db.add(rate)
    if isinstance(value, str):
        rate.value = value
    else:
        rate.value = json.dumps(value, ensure_ascii=False)
    if description is not None:
        rate.description = description
    rate.updated_at = datetime.now(timezone.utc)
    rate.updated_by = updated_by
    db.flush()
    logger.info("cost rate upserted", extra={"key": key})
    return rate


def bulk_upsert_cost_rates(
    db: Session,
    rates: dict,
    updated_by: int | None = None,
) -> list[CostRate]:
    """批量创建或更新费率

    rates 格式: {key: {"value": {...}, "description": "..."}}
    """
    result = []
    for key, data in rates.items():
        rate = upsert_cost_rate(
            db,
            key=key,
            value=data["value"],
            description=data.get("description"),
            updated_by=updated_by,
        )
        result.append(rate)
    return result


# ── Asset cost queries ─────────────────────────────────────────


def get_assets_without_cost_data(db: Session) -> int:
    """统计没有采购价格的资产数量"""
    stmt = select(Asset).where(Asset.purchase_price.is_(None))
    # use the ORM count approach consistent with the rest of the codebase
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(Asset).where(Asset.purchase_price.is_(None))
    return db.scalar(count_stmt) or 0


def get_assets_by_dept(db: Session, dept_id: int) -> list[Asset]:
    """列出归属指定部门的资产"""
    stmt = (
        select(Asset)
        .where(Asset.responsible_dept_id == dept_id)
        .order_by(Asset.id)
    )
    return list(db.scalars(stmt).all())
