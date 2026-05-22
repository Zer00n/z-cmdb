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


# ── 威胁狩猎助手兼容导出 ─────────────────────────────────────

# 品牌字典：product name → vendor
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

# OS 双词品牌白名单（匹配时优先取两个词作为 os_name）
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
    将 os_info 拆分为 (os_name, os_version)。
    示例：
      'Ubuntu 22.04 LTS' → ('Ubuntu', '22.04 LTS')
      'Windows Server 2019' → ('Windows Server', '2019')
      None → ('', '')
    """
    if not os_info:
        return ("", "")
    os_info = os_info.strip()

    # 尝试多词品牌匹配
    for prefix in _OS_MULTI_WORD_PREFIXES:
        if os_info.lower().startswith(prefix.lower()):
            rest = os_info[len(prefix):].strip()
            return (prefix, rest)

    # 单词品牌：第一个空格前为名
    parts = os_info.split(None, 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


def _map_criticality(importance: str) -> str:
    """importance → criticality 映射"""
    mapping = {"core": "high", "important": "medium", "normal": "low"}
    return mapping.get(importance, "low")


def _map_exposure(network_zone: str) -> str:
    """network_zone → exposure_scope 映射"""
    mapping = {
        "dmz": "public",
        "intranet": "internal",
        "office": "office",
        "management": "internal",
        "other": "internal",
    }
    return mapping.get(network_zone, "internal")


def _resolve_vendor(product_name: str | None) -> str:
    """根据 product 名查字典，未命中则返回 product 名本身"""
    if not product_name:
        return ""
    key = product_name.lower().strip()
    return _VENDOR_DICT.get(key, product_name)


def _resolve_environment(business_system: str, default: str = "prod") -> str:
    """
    从 business_system 名称启发式推断 environment。
    前缀匹配：dev-/test-/staging-/uat- → 对应环境；否则返回默认值。
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
    """拼接 tags 字段：asset_type, network_zone, business_system, importance"""
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
    导出资产+应用为威胁狩猎助手兼容 CSV。
    返回 (csv_string, row_count)。
    """
    from app.repositories import asset_app_repo

    # 拉全量资产（不分页）
    params_all = params.model_copy(update={"page": 1, "page_size": 10000})
    if not include_decommissioned:
        # 强制排除已下线
        params_all = params_all.model_copy(update={"status": "online"}) if not params_all.status else params_all
        # 如果用户指定了 status 筛选，尊重用户选择；否则排除 decommissioned
        # 实际逻辑：如果 status 未指定，我们不设 status 过滤但在结果中排除 decommissioned
    assets, _ = asset_repo.list_assets(db, params_all)

    # 排除 decommissioned（如果未通过 params 过滤）
    if not include_decommissioned:
        assets = [a for a in assets if a.status != "decommissioned"]

    # 批量拉应用
    asset_ids = [a.id for a in assets]
    apps_map = asset_app_repo.list_apps_for_assets(db, asset_ids)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # 表头
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
            # 输出一行空 product
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
