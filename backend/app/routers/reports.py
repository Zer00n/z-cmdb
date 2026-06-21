"""
Security report routes
GET /api/reports/dashboard-summary   Dashboard aggregate data
GET /api/reports/port-exposure       Port exposure surface
GET /api/reports/dangerous-ports     Dangerous port list
GET /api/reports/shadow-assets       Shadow assets
GET /api/reports/asset-changes       Asset change timeline
"""
import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser
from app.models.asset import Asset, AssetPort
from app.services import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ── Dashboard aggregate API ────────────────────────────────────

@router.get("/dashboard-summary")
def dashboard_summary(
    force: bool = Query(False, description="Force refresh, bypass cache"),
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """Dashboard aggregate data (single request returns all panel data)"""
    from app.services.dashboard_service import get_summary
    return get_summary(db, force=force)


# ── Port exposure surface ──────────────────────────────────────

@router.get("/port-exposure")
def port_exposure(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Port exposure analysis:
    - Top 10 open ports across all assets
    - Port statistics grouped by network zone
    """
    # Top 10 ports
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

    # Stats by zone
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
    Dangerous port alert list:
    Dangerous port list and high-risk zones are read from system_configs
    """
    dangerous_ports_set = config_service.get_dangerous_ports_list(db)
    dangerous_zones_set = config_service.get_dangerous_zones(db)

    stmt = (
        select(
            Asset.id, Asset.asset_no, Asset.ip_address, Asset.hostname,
            Asset.network_zone, AssetPort.port_number, AssetPort.protocol,
            AssetPort.service_name,
        )
        .join(AssetPort, Asset.id == AssetPort.asset_id)
        .where(AssetPort.state == "open")
        .where(AssetPort.port_number.in_(dangerous_ports_set))
        .where(Asset.status == "online")
        .order_by(Asset.network_zone, AssetPort.port_number)
    )
    rows = db.execute(stmt).all()

    alerts = []
    for row in rows:
        zone = row[4]
        severity = "high" if zone in dangerous_zones_set else "medium"
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
    Shadow asset identification:
    - Assets detected by scan but missing business_system/owner fields
    - Long-term offline assets (missing_count exceeds threshold)
    """
    offline_threshold = config_service.get_shadow_offline_days(db)

    # Assets missing key fields
    incomplete_stmt = (
        select(Asset)
        .where(Asset.source == "scan")
        .where(Asset.status == "online")
        .where(
            (Asset.business_system == "") | (Asset.owner == "")
        )
    )
    incomplete = list(db.scalars(incomplete_stmt).all())

    # Long-term offline (missing_count >= threshold)
    long_offline_stmt = (
        select(Asset)
        .where(Asset.missing_count >= offline_threshold)
        .where(Asset.status.in_(["offline", "online"]))
    )
    long_offline = list(db.scalars(long_offline_stmt).all())

    return {
        "incomplete_assets": [
            {"id": a.id, "asset_no": a.asset_no, "ip_address": a.ip_address,
             "hostname": a.hostname, "reason": "Missing business system or owner"}
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
    Asset change timeline (simplified):
    Returns recent scan snapshot change records
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
    """Export dangerous ports report as CSV"""
    import csv
    import io

    from fastapi import Response

    data = dangerous_ports(_current_user, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["AssetNo", "IPAddress", "Hostname", "NetworkZone", "Port", "Protocol", "Service", "Severity"])
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
    """Export shadow assets report as CSV"""
    import csv
    import io

    from fastapi import Response

    data = shadow_assets(_current_user, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["AssetNo", "IPAddress", "Hostname", "Reason/ConsecutiveMisses"])
    for a in data["incomplete_assets"]:
        writer.writerow([a["asset_no"], a["ip_address"], a["hostname"] or "", a["reason"]])
    for a in data["long_offline_assets"]:
        writer.writerow([a["asset_no"], a["ip_address"], a["hostname"] or "", f"Missed {a['missing_count']} consecutive scans"])
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shadow_assets.csv"},
    )
