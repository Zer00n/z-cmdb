"""
Dashboard aggregation service
Single endpoint returns all dashboard data, with SQL aggregation and module-level TTL cache.
"""
import json
import logging
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetPort
from app.models.audit import AuditLog
from app.models.llm_log import LlmCallLog
from app.models.scan import ScanBatch, ScanSnapshotItem
from app.services import config_service

logger = logging.getLogger(__name__)

# ── Module-level Cache ─────────────────────────────────────────────
_cache_lock = threading.Lock()
_cache_payload: dict | None = None
_cache_ts: float = 0.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_summary(db: Session, force: bool = False) -> dict:
    """
    Return all aggregated dashboard data.
    Uses TTL caching; cache_age_seconds > 0 on cache hit.
    force=True bypasses the cache.
    """
    global _cache_payload, _cache_ts

    ttl = config_service.get_dashboard_refresh_seconds(db)

    with _cache_lock:
        if not force and _cache_payload is not None:
            age = time.time() - _cache_ts
            if age < ttl:
                _cache_payload["cache_age_seconds"] = round(age, 1)
                return _cache_payload

    # Cache miss or forced refresh, re-aggregate
    limit = config_service.get_dashboard_list_limit(db)
    dangerous_ports = config_service.get_dangerous_ports_list(db)
    dangerous_zones = config_service.get_dangerous_zones(db)

    result = {
        "generated_at": _now_iso(),
        "cache_age_seconds": 0,
        "kpi": _build_kpi(db, dangerous_ports, dangerous_zones),
        "asset_distribution": _build_asset_distribution(db),
        "port_exposure": _build_port_exposure(db),
        "dangerous_ports": _build_dangerous_ports(db, dangerous_ports, dangerous_zones, limit),
        "shadow_assets": _build_shadow_assets(db, limit),
        "asset_changes": _build_asset_changes(db, limit),
        "zone_topology": _build_zone_topology(db),
        "activity": _build_activity(db, limit),
    }

    with _cache_lock:
        _cache_payload = result
        _cache_ts = time.time()

    return result


# ── KPI ────────────────────────────────────────────────────

def _build_kpi(db: Session, dangerous_ports: set[int], dangerous_zones: set[str]) -> dict:
    # Asset counts (grouped by status)
    status_rows = db.execute(
        select(Asset.status, func.count()).group_by(Asset.status)
    ).all()
    status_map = {row[0]: row[1] for row in status_rows}
    total = sum(status_map.values())

    # Dangerous port count
    dp_count = db.scalar(
        select(func.count()).select_from(AssetPort)
        .join(Asset, Asset.id == AssetPort.asset_id)
        .where(AssetPort.state == "open")
        .where(AssetPort.port_number.in_(dangerous_ports))
        .where(Asset.status == "online")
    ) or 0

    # Shadow asset count (missing fields + long-term offline)
    incomplete = db.scalar(
        select(func.count()).select_from(Asset)
        .where(Asset.source == "scan")
        .where(Asset.status == "online")
        .where((Asset.business_system == "") | (Asset.owner == ""))
    ) or 0
    long_offline = db.scalar(
        select(func.count()).select_from(Asset)
        .where(Asset.missing_count >= 3)
        .where(Asset.status.in_(["offline", "online"]))
    ) or 0
    shadow_count = incomplete + long_offline

    # New + changed this month (new + changed snapshot items from confirmed batches)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    changes_this_month = db.scalar(
        select(func.count()).select_from(ScanSnapshotItem)
        .join(ScanBatch, ScanBatch.id == ScanSnapshotItem.scan_batch_id)
        .where(ScanBatch.status == "confirmed")
        .where(ScanBatch.uploaded_at >= month_start)
        .where(ScanSnapshotItem.diff_type.in_(["new", "changed"]))
    ) or 0

    # Scan coverage
    last_batch = db.scalar(
        select(ScanBatch).where(ScanBatch.status == "confirmed")
        .order_by(ScanBatch.uploaded_at.desc()).limit(1)
    )
    last_scan_at = last_batch.uploaded_at.isoformat() if last_batch else None
    covered = db.scalar(
        select(func.count()).select_from(Asset)
        .where(Asset.last_seen_at.is_not(None))
        .where(Asset.status != "decommissioned")
    ) or 0
    total_active = total - status_map.get("decommissioned", 0)

    return {
        "total_assets": total,
        "online": status_map.get("online", 0),
        "offline": status_map.get("offline", 0),
        "decommissioned": status_map.get("decommissioned", 0),
        "dangerous_ports": dp_count,
        "shadow_assets": shadow_count,
        "changes_this_month": changes_this_month,
        "scan_coverage": {
            "last_scan_at": last_scan_at,
            "covered": covered,
            "total": total_active,
        },
    }


# ── Asset Distribution ───────────────────────────────────────────────

def _build_asset_distribution(db: Session) -> dict:
    def _group(col):
        rows = db.execute(
            select(col, func.count()).select_from(Asset)
            .where(Asset.status != "decommissioned")
            .group_by(col).order_by(func.count().desc())
        ).all()
        return [{"label": r[0] or "unknown", "count": r[1]} for r in rows]

    return {
        "by_zone": _group(Asset.network_zone),
        "by_type": _group(Asset.asset_type),
        "by_importance": _group(Asset.importance),
        "by_os": _group(Asset.os_info),
    }


# ── Port Exposure ─────────────────────────────────────────────

def _build_port_exposure(db: Session) -> dict:
    top_ports = [
        {"port": r[0], "count": r[1]}
        for r in db.execute(
            select(AssetPort.port_number, func.count().label("count"))
            .where(AssetPort.state == "open")
            .group_by(AssetPort.port_number)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
    ]

    by_zone = [
        {"zone": r[0], "port_count": r[1]}
        for r in db.execute(
            select(Asset.network_zone, func.count(AssetPort.id).label("port_count"))
            .join(AssetPort, Asset.id == AssetPort.asset_id)
            .where(AssetPort.state == "open")
            .where(Asset.status == "online")
            .group_by(Asset.network_zone)
        ).all()
    ]

    return {"top_ports": top_ports, "by_zone": by_zone}


# ── Dangerous Port Alerts ───────────────────────────────────────────

def _build_dangerous_ports(
    db: Session,
    dangerous_ports: set[int],
    dangerous_zones: set[str],
    limit: int,
) -> list[dict]:
    rows = db.execute(
        select(
            Asset.id, Asset.asset_no, Asset.ip_address, Asset.hostname,
            Asset.network_zone, AssetPort.port_number, AssetPort.protocol,
            AssetPort.service_name,
        )
        .join(AssetPort, Asset.id == AssetPort.asset_id)
        .where(AssetPort.state == "open")
        .where(AssetPort.port_number.in_(dangerous_ports))
        .where(Asset.status == "online")
        .order_by(Asset.network_zone, AssetPort.port_number)
        .limit(limit)
    ).all()

    return [
        {
            "asset_id": r[0], "asset_no": r[1], "ip_address": r[2],
            "hostname": r[3], "network_zone": r[4], "port_number": r[5],
            "protocol": r[6], "service_name": r[7],
            "severity": "high" if r[4] in dangerous_zones else "medium",
        }
        for r in rows
    ]


# ── Shadow Assets ───────────────────────────────────────────────

def _build_shadow_assets(db: Session, limit: int) -> dict:
    incomplete = list(db.scalars(
        select(Asset)
        .where(Asset.source == "scan")
        .where(Asset.status == "online")
        .where((Asset.business_system == "") | (Asset.owner == ""))
        .limit(limit)
    ).all())

    long_offline = list(db.scalars(
        select(Asset)
        .where(Asset.missing_count >= 3)
        .where(Asset.status.in_(["offline", "online"]))
        .limit(limit)
    ).all())

    return {
        "missing_fields": [
            {"id": a.id, "asset_no": a.asset_no, "ip_address": a.ip_address,
             "hostname": a.hostname, "reason": "Missing business system or owner"}
            for a in incomplete
        ],
        "missing_fields_count": len(incomplete),
        "long_offline": [
            {"id": a.id, "asset_no": a.asset_no, "ip_address": a.ip_address,
             "hostname": a.hostname, "missing_count": a.missing_count}
            for a in long_offline
        ],
        "long_offline_count": len(long_offline),
    }


# ── Asset Change Timeline ─────────────────────────────────────────

def _build_asset_changes(db: Session, limit: int) -> list[dict]:
    items = list(db.scalars(
        select(ScanSnapshotItem)
        .where(ScanSnapshotItem.diff_type.in_(["new", "changed", "restored"]))
        .order_by(ScanSnapshotItem.id.desc())
        .limit(limit)
    ).all())

    return [
        {
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


# ── Zone Topology ───────────────────────────────────────────────

def _build_zone_topology(db: Session) -> dict:
    from sqlalchemy import case

    rows = db.execute(
        select(
            Asset.network_zone,
            func.count().label("asset_count"),
            func.sum(case((Asset.importance == "core", 1), else_=0)).label("core_count"),
        )
        .where(Asset.status != "decommissioned")
        .group_by(Asset.network_zone)
    ).all()

    return {
        "zones": [
            {"zone": r[0], "asset_count": r[1], "core_count": r[2]}
            for r in rows
        ]
    }


# ── Audit and LLM Activity Stream ─────────────────────────────────────

def _build_activity(db: Session, limit: int) -> list[dict]:
    # Merge audit_logs + llm_call_logs, take top N by reverse timestamp
    audit_items = list(db.scalars(
        select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    ).all())

    llm_items = list(db.scalars(
        select(LlmCallLog)
        .order_by(LlmCallLog.timestamp.desc())
        .limit(limit)
    ).all())

    combined = []
    for log in audit_items:
        combined.append({
            "timestamp": log.timestamp.isoformat(),
            "action_type": log.action_type,
            "username": log.username,
            "target": f"{log.target_type or ''} {log.target_id or ''}".strip(),
            "result": log.result,
            "source": "audit",
        })
    for log in llm_items:
        combined.append({
            "timestamp": log.timestamp.isoformat(),
            "action_type": "LLM_CALL",
            "username": str(log.user_id) if log.user_id else "",
            "target": f"{log.provider}/{log.model}" if log.provider else "",
            "result": "success" if log.success else "failed",
            "source": "llm",
        })

    combined.sort(key=lambda x: x["timestamp"], reverse=True)
    return combined[:limit]
