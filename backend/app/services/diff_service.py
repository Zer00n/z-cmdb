"""
扫描差异分析引擎
实现 NEW / CHANGED / MISSING / RESTORED 四种差异类型
"""
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetPort
from app.repositories import asset_repo
from app.utils.nmap_parser import ParsedHost, ParsedPort

logger = logging.getLogger(__name__)


@dataclass
class DiffPort:
    """端口差异"""
    port_number: int
    protocol: str
    old_service: str | None = None
    new_service: str | None = None
    old_version: str | None = None
    new_version: str | None = None
    old_state: str | None = None
    new_state: str | None = None


@dataclass
class DiffResult:
    """单个主机的差异结果"""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    os_info: str | None = None
    diff_type: str = ""  # NEW / CHANGED / SAME / MISSING / RESTORED
    matched_asset_id: int | None = None
    matched_asset_no: str | None = None
    ports: list[ParsedPort] = field(default_factory=list)
    port_changes: list[DiffPort] = field(default_factory=list)


@dataclass
class ScanDiffSummary:
    """扫描差异汇总"""
    new_hosts: list[DiffResult] = field(default_factory=list)
    changed_hosts: list[DiffResult] = field(default_factory=list)
    same_hosts: list[DiffResult] = field(default_factory=list)
    missing_assets: list[DiffResult] = field(default_factory=list)
    restored_assets: list[DiffResult] = field(default_factory=list)

    @property
    def new_count(self) -> int:
        return len(self.new_hosts)

    @property
    def changed_count(self) -> int:
        return len(self.changed_hosts)

    @property
    def missing_count(self) -> int:
        return len(self.missing_assets)


def match_asset(db: Session, host: ParsedHost) -> Asset | None:
    """
    资产匹配逻辑（PRD 4.2.3）：
    1. 优先按 MAC 匹配
    2. 次按 IP 匹配
    3. 兜底按 hostname + OS 匹配
    """
    # MAC 优先
    if host.mac_address:
        asset = asset_repo.get_by_mac(db, host.mac_address)
        if asset:
            return asset

    # IP 匹配
    asset = asset_repo.get_by_ip(db, host.ip_address)
    if asset:
        return asset

    # 兜底：hostname + OS 匹配
    if host.hostname:
        from sqlalchemy import select
        stmt = select(Asset).where(
            Asset.hostname == host.hostname,
            Asset.status != "decommissioned",
        )
        if host.os_info:
            stmt = stmt.where(Asset.os_info == host.os_info)
        asset = db.scalar(stmt)
        if asset:
            return asset

    return None


def compute_port_diff(
    existing_ports: list[AssetPort],
    scanned_ports: list[ParsedPort],
) -> tuple[bool, list[DiffPort]]:
    """
    对比端口变化。
    返回 (has_changes, port_changes)
    """
    existing_map: dict[tuple[int, str], AssetPort] = {
        (p.port_number, p.protocol): p for p in existing_ports
    }
    scanned_map: dict[tuple[int, str], ParsedPort] = {
        (p.port_number, p.protocol): p for p in scanned_ports
    }

    changes: list[DiffPort] = []
    has_changes = False

    # 检查新增和变更的端口
    for key, sp in scanned_map.items():
        ep = existing_map.get(key)
        if ep is None:
            # 新端口
            changes.append(DiffPort(
                port_number=sp.port_number,
                protocol=sp.protocol,
                new_service=sp.service_name,
                new_version=sp.service_version,
                new_state=sp.state,
            ))
            has_changes = True
        else:
            # 检查服务/版本/状态是否变化
            svc_changed = (ep.service_name or "") != (sp.service_name or "")
            ver_changed = (ep.service_version or "") != (sp.service_version or "")
            state_changed = (ep.state or "open") != (sp.state or "open")
            if svc_changed or ver_changed or state_changed:
                changes.append(DiffPort(
                    port_number=sp.port_number,
                    protocol=sp.protocol,
                    old_service=ep.service_name,
                    new_service=sp.service_name,
                    old_version=ep.service_version,
                    new_version=sp.service_version,
                    old_state=ep.state,
                    new_state=sp.state,
                ))
                has_changes = True

    # 检查消失的端口（存在于资产但本次未扫到）
    for key, ep in existing_map.items():
        if key not in scanned_map and ep.state == "open":
            changes.append(DiffPort(
                port_number=ep.port_number,
                protocol=ep.protocol,
                old_service=ep.service_name,
                old_version=ep.service_version,
                old_state=ep.state,
                new_state="closed",
            ))
            has_changes = True

    return has_changes, changes


def compute_diff(db: Session, scanned_hosts: list[ParsedHost]) -> ScanDiffSummary:
    """
    计算扫描结果与现有资产的差异。
    同时检测 MISSING（已有资产本次未扫到）和 RESTORED（之前 missing 本次又扫到）。
    """
    summary = ScanDiffSummary()

    # 记录本次扫到的资产 ID，用于检测 MISSING
    scanned_asset_ids: set[int] = set()

    for host in scanned_hosts:
        asset = match_asset(db, host)

        if asset is None:
            # NEW：未匹配到任何资产
            result = DiffResult(
                ip_address=host.ip_address,
                mac_address=host.mac_address,
                hostname=host.hostname,
                os_info=host.os_info,
                diff_type="NEW",
                ports=host.ports,
            )
            summary.new_hosts.append(result)
        else:
            scanned_asset_ids.add(asset.id)

            # 检查是否为 RESTORED（之前 missing_count > 0）
            is_restored = asset.missing_count > 0

            # 对比端口变化
            existing_ports = asset_repo.get_ports_by_asset(db, asset.id)
            has_changes, port_changes = compute_port_diff(existing_ports, host.ports)

            if is_restored:
                result = DiffResult(
                    ip_address=host.ip_address,
                    mac_address=host.mac_address,
                    hostname=host.hostname,
                    os_info=host.os_info,
                    diff_type="RESTORED",
                    matched_asset_id=asset.id,
                    matched_asset_no=asset.asset_no,
                    ports=host.ports,
                    port_changes=port_changes,
                )
                summary.restored_assets.append(result)
            elif has_changes:
                result = DiffResult(
                    ip_address=host.ip_address,
                    mac_address=host.mac_address,
                    hostname=host.hostname,
                    os_info=host.os_info,
                    diff_type="CHANGED",
                    matched_asset_id=asset.id,
                    matched_asset_no=asset.asset_no,
                    ports=host.ports,
                    port_changes=port_changes,
                )
                summary.changed_hosts.append(result)
            else:
                result = DiffResult(
                    ip_address=host.ip_address,
                    diff_type="SAME",
                    matched_asset_id=asset.id,
                    matched_asset_no=asset.asset_no,
                )
                summary.same_hosts.append(result)

    # 检测 MISSING：在线资产本次未扫到
    from app.schemas.asset import AssetQueryParams
    all_online_params = AssetQueryParams(page=1, page_size=100000, status="online")
    online_assets, _ = asset_repo.list_assets(db, all_online_params)

    for asset in online_assets:
        if asset.id not in scanned_asset_ids:
            result = DiffResult(
                ip_address=asset.ip_address,
                mac_address=asset.mac_address,
                hostname=asset.hostname,
                diff_type="MISSING",
                matched_asset_id=asset.id,
                matched_asset_no=asset.asset_no,
            )
            summary.missing_assets.append(result)

    logger.info(
        "scan diff computed",
        extra={
            "new": summary.new_count,
            "changed": summary.changed_count,
            "missing": summary.missing_count,
            "restored": len(summary.restored_assets),
            "same": len(summary.same_hosts),
        },
    )
    return summary
