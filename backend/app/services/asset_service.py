"""
Asset business logic
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
        raise ValidationError("Asset is already in decommissioned status")
    asset_repo.decommission_asset(db, asset)
    db.commit()
    return asset


def export_assets_csv(db: Session, params: AssetQueryParams) -> str:
    """Export asset list as a CSV string"""
    # Export all without pagination
    params_all = params.model_copy(update={"page": 1, "page_size": 10000})
    assets, _ = asset_repo.list_assets(db, params_all)

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV header
    writer.writerow([
        "Asset No.", "IP Address", "MAC Address", "Hostname", "Asset Type",
        "OS", "Physical Location", "Owner", "Business System",
        "Importance", "Network Zone", "Status", "Source",
        "Last Scan Time", "Created At",
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
    Get asset port change history (based on scan_snapshot_items).
    Returns a timeline of port changes grouped by scan batch.
    """
    from sqlalchemy import select

    from app.models.scan import ScanBatch, ScanSnapshotItem

    # Confirm the asset exists
    asset = asset_repo.get_by_id(db, asset_id)

    # Find all snapshot items associated with this asset's IP
    stmt = (
        select(ScanSnapshotItem, ScanBatch.batch_name, ScanBatch.uploaded_at)
        .join(ScanBatch, ScanSnapshotItem.scan_batch_id == ScanBatch.id)
        .where(ScanSnapshotItem.ip_address == asset.ip_address)
        .where(ScanSnapshotItem.port_number.isnot(None))
        .order_by(ScanBatch.uploaded_at.desc(), ScanSnapshotItem.port_number)
    )
    rows = db.execute(stmt).all()

    # Group by batch
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
    """Batch update asset fields, returns the actual number of updated rows"""
    from sqlalchemy import select, update

    stmt = (
        update(Asset)
        .where(Asset.id.in_(asset_ids))
        .values(**updates, updated_at=datetime.now(timezone.utc))
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount  # type: ignore[return-value]


# ── Threat Hunting Helper Compatible Export ─────────────────────────────────────

# Brand dictionary: product name -> vendor
_VENDOR_DICT: dict[str, str] = {
    "mysql": "Oracle",
    "mariadb": "MariaDB Foundation",
    "postgresql": "PostgreSQL Global Development Group",
    "postgres": "PostgreSQL Global Development Group",
    "mssql": "Microsoft",
    "sqlserver": "Microsoft",
    "oracle": "Oracle",
    "redis": "Redis Ltd",
    "mongodb": "MongoDB Inc",
    "nginx": "nginx",
    "apache": "Apache Software Foundation",
    "httpd": "Apache Software Foundation",
    "tomcat": "Apache Software Foundation",
    "iis": "Microsoft",
    "openssh": "OpenBSD",
    "sshd": "OpenBSD",
    "docker": "Docker Inc",
    "elasticsearch": "Elastic",
    "kibana": "Elastic",
    "rabbitmq": "VMware",
    "kafka": "Apache Software Foundation",
    "zookeeper": "Apache Software Foundation",
    "jenkins": "Jenkins",
    "gitlab": "GitLab Inc",
    "vsftpd": "vsftpd",
    "proftpd": "ProFTPD",
    "postfix": "Postfix",
    "dovecot": "Dovecot",
    "haproxy": "HAProxy Technologies",
    "memcached": "Memcached",
}

# OS multi-word brand whitelist (prefer taking two words as os_name during matching)
_OS_MULTI_WORD_PREFIXES = [
    "Windows Server",
    "Red Hat",
    "Rocky Linux",
    "Alma Linux",
    "AlmaLinux",
    "Oracle Linux",
    "SUSE Linux",
    "openSUSE Leap",
    "Amazon Linux",
    "Mac OS",
    "macOS",
]


def _split_os(os_info: str | None) -> tuple[str, str]:
    """
    Split os_info into (os_name, os_version).
    Examples:
      'Ubuntu 22.04 LTS' -> ('Ubuntu', '22.04 LTS')
      'Windows Server 2019' -> ('Windows Server', '2019')
      None -> ('', '')
    """
    if not os_info:
        return ("", "")
    os_info = os_info.strip()

    # Try multi-word brand matching
    for prefix in _OS_MULTI_WORD_PREFIXES:
        if os_info.lower().startswith(prefix.lower()):
            rest = os_info[len(prefix):].strip()
            return (prefix, rest)

    # Single-word brand: text before first space is the name
    parts = os_info.split(None, 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


def _map_criticality(importance: str) -> str:
    """importance -> criticality mapping"""
    mapping = {"core": "high", "important": "medium", "normal": "low"}
    return mapping.get(importance, "low")


def _map_exposure(network_zone: str) -> str:
    """network_zone -> exposure_scope mapping"""
    mapping = {
        "dmz": "public",
        "intranet": "internal",
        "office": "office",
        "management": "internal",
        "other": "internal",
    }
    return mapping.get(network_zone, "internal")


def _resolve_vendor(product_name: str | None) -> str:
    """Look up product name in the vendor dictionary; returns the product name itself if not found"""
    if not product_name:
        return ""
    key = product_name.lower().strip()
    return _VENDOR_DICT.get(key, product_name)


def _resolve_environment(business_system: str, default: str = "prod") -> str:
    """
    Heuristically infer environment from business_system name.
    Prefix matching: dev-/test-/staging-/uat- -> corresponding environment; otherwise returns default.
    """
    bs_lower = business_system.lower() if business_system else ""
    for prefix, env in [
        ("dev-", "dev"), ("dev_", "dev"),
        ("test-", "test"), ("test_", "test"),
        ("staging-", "staging"), ("staging_", "staging"),
        ("uat-", "staging"), ("uat_", "staging"),
        ("pre-", "staging"), ("pre_", "staging"),
    ]:
        if bs_lower.startswith(prefix):
            return env
    return default


def _build_tags(asset: Asset) -> str:
    """Build tags field: asset_type, network_zone, business_system, importance"""
    parts = [
        asset.asset_type or "",
        asset.network_zone or "",
        asset.business_system or "",
        asset.importance or "",
    ]
    return ",".join(p for p in parts if p)


def export_assets_threat_hunting_csv(
    db: Session,
    params: AssetQueryParams,
    *,
    skip_empty_apps: bool = False,
    include_decommissioned: bool = False,
    default_environment: str = "prod",
) -> tuple[str, int]:
    """
    Export assets + applications as a threat-hunting-compatible CSV.
    Returns (csv_string, row_count).
    """
    from app.repositories import asset_app_repo

    # Fetch all assets (no pagination)
    params_all = params.model_copy(update={"page": 1, "page_size": 10000})
    if not include_decommissioned:
        # Force exclude decommissioned
        params_all = params_all.model_copy(update={"status": "online"}) if not params_all.status else params_all
        # If user specified a status filter, respect their choice; otherwise exclude decommissioned
        # Actual logic: if status is not set, we don't apply a status filter but exclude decommissioned from results
    assets, _ = asset_repo.list_assets(db, params_all)

    # Exclude decommissioned (if not already filtered by params)
    if not include_decommissioned:
        assets = [a for a in assets if a.status != "decommissioned"]

    # Batch fetch applications
    asset_ids = [a.id for a in assets]
    apps_map = asset_app_repo.list_apps_for_assets(db, asset_ids)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # CSV header
    writer.writerow([
        "ip", "hostname", "os_name", "os_version", "environment",
        "criticality", "owner", "tags", "product", "version",
        "vendor", "port", "protocol", "exposure_scope", "notes",
    ])

    row_count = 0
    for asset in assets:
        os_name, os_version = _split_os(asset.os_info)
        environment = _resolve_environment(asset.business_system, default_environment)
        criticality = _map_criticality(asset.importance)
        tags = _build_tags(asset)
        exposure_scope = _map_exposure(asset.network_zone)
        asset_notes = (asset.remark or "").replace("\n", " ").replace("\r", "")

        apps = apps_map.get(asset.id, [])

        if not apps:
            if skip_empty_apps:
                continue
            # Output a row with empty product
            writer.writerow([
                asset.ip_address,
                asset.hostname or "",
                os_name,
                os_version,
                environment,
                criticality,
                asset.owner or "",
                tags,
                "",  # product
                "",  # version
                "",  # vendor
                "",  # port
                "",  # protocol
                exposure_scope,
                asset_notes,
            ])
            row_count += 1
        else:
            for app in apps:
                app_notes = (app.notes or "").replace("\n", " ").replace("\r", "")
                combined_notes = "; ".join(n for n in [asset_notes, app_notes] if n)
                port_str = str(app.port) if app.port else ""
                protocol_str = app.protocol or ""
                writer.writerow([
                    asset.ip_address,
                    asset.hostname or "",
                    os_name,
                    os_version,
                    environment,
                    criticality,
                    asset.owner or "",
                    tags,
                    app.name or "",
                    app.version or "",
                    _resolve_vendor(app.name),
                    port_str,
                    protocol_str,
                    exposure_scope,
                    combined_notes,
                ])
                row_count += 1

    return output.getvalue(), row_count
