"""
安全报表路由
GET /api/reports/port-exposure     端口暴露面
GET /api/reports/dangerous-ports   危险端口列表
GET /api/reports/shadow-assets     影子资产
GET /api/reports/asset-changes     资产变化时间线
"""
import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.models.asset import Asset, AssetPort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

# PRD 12.2 危险端口清单
DANGEROUS_PORTS = {
    21, 22, 23, 135, 139, 445, 1433, 1521, 2375,
    3306, 3389, 5432, 5984, 6379, 8080, 8888, 9200, 11211, 27017,
}

# 高危区域（暴露在这些区域的危险端口为高危）
HIGH_RISK_ZONES = {"dmz", "office"}


@router.get("/port-exposure")
def port_exposure(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    端口暴露面分析：
    - 全网开放端口 Top 10
    - 按网络区域分组的端口统计
    """
    # Top 10 端口
    top_ports_stmt = (
        select(AssetPort.port_number, func.count().label("count"))
        .where(AssetPort.state == "open")
        .group_by(AssetPort.port_number)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_ports = [
        {"port": row[0], "count": row[1]}
        for row in db.execute(top_ports_stmt).all()
    ]

    # 按区域统计
    zone_stats_stmt = (
        select(Asset.network_zone, func.count(AssetPort.id).label("port_count"))
        .join(AssetPort, Asset.id == AssetPort.asset_id)
        .where(AssetPort.state == "open")
        .where(Asset.status == "online")
        .group_by(Asset.network_zone)
    )
    zone_stats = [
        {"zone": row[0], "port_count": row[1]}
        for row in db.execute(zone_stats_stmt).all()
    ]

    return {"top_ports": top_ports, "zone_stats": zone_stats}


@router.get("/dangerous-ports")
def dangerous_ports(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    危险端口告警列表：
    暴露在 DMZ 或办公网的危险端口为高危，内网为中危
    """
    stmt = (
        select(
            Asset.id, Asset.asset_no, Asset.ip_address, Asset.hostname,
            Asset.network_zone, AssetPort.port_number, AssetPort.protocol,
            AssetPort.service_name,
        )
        .join(AssetPort, Asset.id == AssetPort.asset_id)
        .where(AssetPort.state == "open")
        .where(AssetPort.port_number.in_(DANGEROUS_PORTS))
        .where(Asset.status == "online")
        .order_by(Asset.network_zone, AssetPort.port_number)
    )
    rows = db.execute(stmt).all()

    alerts = []
    for row in rows:
        zone = row[4]
        severity = "high" if zone in HIGH_RISK_ZONES else "medium"
        alerts.append({
            "asset_id": row[0],
            "asset_no": row[1],
            "ip_address": row[2],
            "hostname": row[3],
            "network_zone": zone,
            "port_number": row[5],
            "protocol": row[6],
            "service_name": row[7],
            "severity": severity,
        })

    return {
        "total": len(alerts),
        "high_count": sum(1 for a in alerts if a["severity"] == "high"),
        "medium_count": sum(1 for a in alerts if a["severity"] == "medium"),
        "alerts": alerts,
    }


@router.get("/shadow-assets")
def shadow_assets(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    影子资产识别：
    - 被扫到但缺少业务系统/负责人字段的资产
    - 长期 offline 的资产（missing_count >= 3）
    """
    # 缺少关键字段的资产
    incomplete_stmt = (
        select(Asset)
        .where(Asset.source == "scan")
        .where(Asset.status == "online")
        .where(
            (Asset.business_system == "") | (Asset.owner == "")
        )
    )
    incomplete = list(db.scalars(incomplete_stmt).all())

    # 长期 offline
    long_offline_stmt = (
        select(Asset)
        .where(Asset.missing_count >= 3)
        .where(Asset.status.in_(["offline", "online"]))
    )
    long_offline = list(db.scalars(long_offline_stmt).all())

    return {
        "incomplete_assets": [
            {"id": a.id, "asset_no": a.asset_no, "ip_address": a.ip_address,
             "hostname": a.hostname, "reason": "缺少业务系统或负责人"}
            for a in incomplete
        ],
        "long_offline_assets": [
            {"id": a.id, "asset_no": a.asset_no, "ip_address": a.ip_address,
             "hostname": a.hostname, "missing_count": a.missing_count}
            for a in long_offline
        ],
        "total": len(incomplete) + len(long_offline),
    }


@router.get("/asset-changes")
def asset_changes(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    资产变化时间线（简化版）：
    返回最近的扫描快照变化记录
    """
    from app.models.scan import ScanSnapshotItem
    stmt = (
        select(ScanSnapshotItem)
        .where(ScanSnapshotItem.diff_type.in_(["new", "changed"]))
        .order_by(ScanSnapshotItem.id.desc())
        .limit(100)
    )
    items = list(db.scalars(stmt).all())

    changes = [
        {
            "id": item.id,
            "batch_id": item.scan_batch_id,
            "ip_address": item.ip_address,
            "hostname": item.hostname,
            "port_number": item.port_number,
            "protocol": item.protocol,
            "service_name": item.service_name,
            "diff_type": item.diff_type,
        }
        for item in items
    ]

    return {"total": len(changes), "changes": changes}


@router.get("/dangerous-ports/export")
def export_dangerous_ports(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """导出危险端口报表为 CSV"""
    import csv
    import io

    from fastapi import Response

    data = dangerous_ports(_current_user, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["资产编号", "IP地址", "主机名", "网络区域", "端口", "协议", "服务", "严重性"])
    for a in data["alerts"]:
        writer.writerow([
            a["asset_no"], a["ip_address"], a["hostname"] or "",
            a["network_zone"], a["port_number"], a["protocol"],
            a["service_name"] or "", a["severity"],
        ])
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dangerous_ports.csv"},
    )


@router.get("/shadow-assets/export")
def export_shadow_assets(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """导出影子资产报表为 CSV"""
    import csv
    import io

    from fastapi import Response

    data = shadow_assets(_current_user, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["资产编号", "IP地址", "主机名", "原因/连续未扫到次数"])
    for a in data["incomplete_assets"]:
        writer.writerow([a["asset_no"], a["ip_address"], a["hostname"] or "", a["reason"]])
    for a in data["long_offline_assets"]:
        writer.writerow([a["asset_no"], a["ip_address"], a["hostname"] or "", f"连续未扫到 {a['missing_count']} 次"])
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shadow_assets.csv"},
    )
