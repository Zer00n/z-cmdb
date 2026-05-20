"""
资产业务逻辑
"""
import csv
import io
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AssetNotFoundError, ValidationError
from app.models.asset import Asset
from app.repositories import asset_repo
from app.schemas.asset import AssetCreate, AssetListResponse, AssetQueryParams, AssetUpdate

logger = logging.getLogger(__name__)


def get_asset(db: Session, asset_id: int) -> Asset:
    return asset_repo.get_by_id(db, asset_id, load_ports=True)


def list_assets(db: Session, params: AssetQueryParams) -> AssetListResponse:
    assets, total = asset_repo.list_assets(db, params)
    total_pages = max(1, (total + params.page_size - 1) // params.page_size)
    return AssetListResponse(
        items=assets,  # type: ignore[arg-type]
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


def create_asset(db: Session, data: AssetCreate) -> Asset:
    asset = asset_repo.create_asset(
        db,
        asset_no=data.asset_no,
        ip_address=data.ip_address,
        mac_address=data.mac_address,
        hostname=data.hostname,
        asset_type=data.asset_type,
        os_info=data.os_info,
        location=data.location,
        owner=data.owner,
        business_system=data.business_system,
        importance=data.importance,
        network_zone=data.network_zone,
        cpu=data.cpu,
        memory_gb=data.memory_gb,
        disk_gb=data.disk_gb,
        purchase_date=data.purchase_date,
        warranty_expiry=data.warranty_expiry,
        remark=data.remark,
        source=data.source,
        status="online",
    )
    db.commit()
    return asset_repo.get_by_id(db, asset.id, load_ports=True)


def update_asset(db: Session, asset_id: int, data: AssetUpdate) -> Asset:
    asset = asset_repo.get_by_id(db, asset_id)
    update_data = data.model_dump(exclude_none=True)
    asset_repo.update_asset(db, asset, **update_data)
    db.commit()
    return asset_repo.get_by_id(db, asset_id, load_ports=True)


def decommission_asset(db: Session, asset_id: int) -> Asset:
    asset = asset_repo.get_by_id(db, asset_id)
    if asset.status == "decommissioned":
        raise ValidationError("资产已处于下线状态")
    asset_repo.decommission_asset(db, asset)
    db.commit()
    return asset


def export_assets_csv(db: Session, params: AssetQueryParams) -> str:
    """导出资产列表为 CSV 字符串"""
    # 导出不分页，取全量
    params_all = params.model_copy(update={"page": 1, "page_size": 10000})
    assets, _ = asset_repo.list_assets(db, params_all)

    output = io.StringIO()
    writer = csv.writer(output)

    # 表头
    writer.writerow([
        "资产编号", "IP地址", "MAC地址", "主机名", "资产类型",
        "操作系统", "物理位置", "负责人", "业务系统",
        "重要性", "网络区域", "状态", "来源",
        "最后扫描时间", "创建时间",
    ])

    for a in assets:
        writer.writerow([
            a.asset_no, a.ip_address, a.mac_address or "",
            a.hostname or "", a.asset_type, a.os_info or "",
            a.location, a.owner, a.business_system,
            a.importance, a.network_zone, a.status, a.source,
            a.last_seen_at.isoformat() if a.last_seen_at else "",
            a.created_at.isoformat(),
        ])

    return output.getvalue()


def get_asset_history(db: Session, asset_id: int) -> dict:
    """
    获取资产端口变化历史（基于 scan_snapshot_items）。
    返回按批次分组的端口变化时间线。
    """
    from sqlalchemy import select

    from app.models.scan import ScanBatch, ScanSnapshotItem

    # 确认资产存在
    asset = asset_repo.get_by_id(db, asset_id)

    # 查找所有关联此资产 IP 的快照项
    stmt = (
        select(ScanSnapshotItem, ScanBatch.batch_name, ScanBatch.uploaded_at)
        .join(ScanBatch, ScanSnapshotItem.scan_batch_id == ScanBatch.id)
        .where(ScanSnapshotItem.ip_address == asset.ip_address)
        .where(ScanSnapshotItem.port_number.isnot(None))
        .order_by(ScanBatch.uploaded_at.desc(), ScanSnapshotItem.port_number)
    )
    rows = db.execute(stmt).all()

    # 按批次分组
    batches_map: dict[int, dict] = {}
    for item, batch_name, uploaded_at in rows:
        bid = item.scan_batch_id
        if bid not in batches_map:
            batches_map[bid] = {
                "batch_id": bid,
                "batch_name": batch_name,
                "scan_time": uploaded_at.isoformat() if uploaded_at else None,
                "diff_type": item.diff_type,
                "ports": [],
            }
        batches_map[bid]["ports"].append({
            "port_number": item.port_number,
            "protocol": item.protocol,
            "service_name": item.service_name,
            "service_version": item.service_version,
        })

    return {
        "asset_id": asset.id,
        "asset_no": asset.asset_no,
        "ip_address": asset.ip_address,
        "history": list(batches_map.values()),
    }


def bulk_update(db: Session, asset_ids: list[int], updates: dict) -> int:
    """批量更新资产字段，返回实际更新数量"""
    from sqlalchemy import select, update

    stmt = (
        update(Asset)
        .where(Asset.id.in_(asset_ids))
        .values(**updates, updated_at=datetime.now(timezone.utc))
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount  # type: ignore[return-value]
