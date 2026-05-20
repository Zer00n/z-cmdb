"""
扫描批次业务逻辑
上传、解析、差异分析、确认导入
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    NmapParseError,
    ScanBatchNotFoundError,
    ValidationError,
)
from app.models.asset import Asset
from app.models.scan import ScanBatch, ScanSnapshotItem
from app.repositories import asset_repo
from app.services.diff_service import compute_diff
from app.utils.nmap_parser import ParsedHost, parse_nmap_xml

logger = logging.getLogger(__name__)


def upload_and_parse(
    db: Session,
    file_content: bytes,
    filename: str,
    user_id: int,
) -> ScanBatch:
    """
    上传 nmap XML 文件，解析并创建扫描批次。
    返回 ScanBatch（status=pending）。
    """
    # 文件大小校验（从系统配置读取上限）
    from app.services.config_service import get_upload_max_size_mb
    max_mb = get_upload_max_size_mb(db)
    max_bytes = max_mb * 1024 * 1024
    if len(file_content) > max_bytes:
        raise FileTooLargeError(
            f"文件大小 {len(file_content) / 1024 / 1024:.1f}MB 超过限制 {max_mb}MB"
        )

    # 文件类型校验
    if not filename.lower().endswith(".xml"):
        raise InvalidFileTypeError("仅支持 .xml 格式的 nmap 扫描报告")

    # 解析 XML
    parsed = parse_nmap_xml(file_content)

    # 保存文件（UUID 命名，防猜测）
    upload_dir = Path(__file__).parent.parent.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.xml"
    file_path = upload_dir / safe_name
    file_path.write_bytes(file_content)

    # 创建批次记录
    batch = ScanBatch(
        batch_name=filename,
        uploaded_by=user_id,
        uploaded_at=datetime.now(timezone.utc),
        scan_started_at=None,  # TODO: 从 parsed 提取
        scan_finished_at=None,
        file_path=str(file_path),
        file_size_bytes=len(file_content),
        total_hosts=len(parsed.hosts),
        status="pending",
    )
    db.add(batch)
    db.flush()

    # 计算差异
    diff_summary = compute_diff(db, parsed.hosts)
    batch.new_count = diff_summary.new_count
    batch.changed_count = diff_summary.changed_count
    batch.missing_count = diff_summary.missing_count

    # 保存快照项
    for host in parsed.hosts:
        for port in host.ports:
            item = ScanSnapshotItem(
                scan_batch_id=batch.id,
                ip_address=host.ip_address,
                mac_address=host.mac_address,
                hostname=host.hostname,
                os_info=host.os_info,
                port_number=port.port_number,
                protocol=port.protocol,
                service_name=port.service_name,
                service_version=port.service_version,
                diff_type=_get_host_diff_type(host, diff_summary),
            )
            db.add(item)

        # 如果主机没有端口，也要记录一条
        if not host.ports:
            item = ScanSnapshotItem(
                scan_batch_id=batch.id,
                ip_address=host.ip_address,
                mac_address=host.mac_address,
                hostname=host.hostname,
                os_info=host.os_info,
                diff_type=_get_host_diff_type(host, diff_summary),
            )
            db.add(item)

    db.commit()
    logger.info(
        "scan batch created",
        extra={
            "batch_id": batch.id,
            "total_hosts": batch.total_hosts,
            "new": batch.new_count,
            "changed": batch.changed_count,
            "missing": batch.missing_count,
        },
    )
    return batch


def _get_host_diff_type(host: ParsedHost, diff_summary) -> str:
    """获取主机的差异类型"""
    for r in diff_summary.new_hosts:
        if r.ip_address == host.ip_address:
            return "new"
    for r in diff_summary.changed_hosts:
        if r.ip_address == host.ip_address:
            return "changed"
    for r in diff_summary.restored_assets:
        if r.ip_address == host.ip_address:
            return "restored"
    return "same"


def get_batch(db: Session, batch_id: int) -> ScanBatch:
    batch = db.get(ScanBatch, batch_id)
    if batch is None:
        raise ScanBatchNotFoundError(f"扫描批次 {batch_id} 不存在")
    return batch


def get_batch_diff(db: Session, batch_id: int):
    """
    获取扫描批次的差异详情，返回 ScanDiffResponse。
    基于 scan_snapshot_items 中的 diff_type 分组，并补充端口变更细节。
    """
    from sqlalchemy import select as sa_select

    from app.schemas.scan import (
        DiffChangedHost,
        DiffHostPortChange,
        DiffMissingHost,
        DiffNewHost,
        DiffPortRead,
        ScanDiffResponse,
    )

    batch = get_batch(db, batch_id)

    # 获取所有快照项
    items = list(db.scalars(
        sa_select(ScanSnapshotItem).where(ScanSnapshotItem.scan_batch_id == batch_id)
    ).all())

    # 按 IP 分组
    hosts_by_ip: dict[str, list[ScanSnapshotItem]] = {}
    for item in items:
        hosts_by_ip.setdefault(item.ip_address, []).append(item)

    new_hosts: list[DiffNewHost] = []
    changed_hosts: list[DiffChangedHost] = []
    missing_hosts: list[DiffMissingHost] = []

    for ip, host_items in hosts_by_ip.items():
        first = host_items[0]
        diff_type = first.diff_type or "same"

        if diff_type == "new":
            ports = [
                DiffPortRead(
                    port_number=item.port_number,
                    protocol=item.protocol or "tcp",
                    service_name=item.service_name,
                    service_version=item.service_version,
                    state="open",
                )
                for item in host_items
                if item.port_number is not None
            ]
            new_hosts.append(DiffNewHost(
                ip_address=ip,
                mac_address=first.mac_address,
                hostname=first.hostname,
                os_info=first.os_info,
                ports=ports,
            ))

        elif diff_type in ("changed", "restored"):
            # 获取当前资产端口
            scan_ports = [
                DiffPortRead(
                    port_number=item.port_number,
                    protocol=item.protocol or "tcp",
                    service_name=item.service_name,
                    service_version=item.service_version,
                    state="open",
                )
                for item in host_items
                if item.port_number is not None
            ]

            # 获取当前资产信息
            asset = asset_repo.get_by_ip(db, ip)
            current_ports: list[DiffPortRead] = []
            port_changes: list[DiffHostPortChange] = []
            matched_asset_id = None
            matched_asset_no = None

            if asset:
                matched_asset_id = asset.id
                matched_asset_no = asset.asset_no
                existing_ports = asset_repo.get_ports_by_asset(db, asset.id)
                current_ports = [
                    DiffPortRead(
                        port_number=p.port_number,
                        protocol=p.protocol,
                        service_name=p.service_name,
                        service_version=p.service_version,
                        state=p.state,
                    )
                    for p in existing_ports
                ]

                # 计算端口变更
                existing_map = {(p.port_number, p.protocol): p for p in existing_ports}
                scanned_map = {(p.port_number, p.protocol): p for p in scan_ports}

                for key, sp in scanned_map.items():
                    ep = existing_map.get(key)
                    if ep is None:
                        port_changes.append(DiffHostPortChange(
                            port_number=sp.port_number,
                            protocol=sp.protocol,
                            new_service=sp.service_name,
                            new_version=sp.service_version,
                            new_state=sp.state,
                            change_type="added",
                        ))
                    else:
                        svc_changed = (ep.service_name or "") != (sp.service_name or "")
                        ver_changed = (ep.service_version or "") != (sp.service_version or "")
                        if svc_changed or ver_changed:
                            port_changes.append(DiffHostPortChange(
                                port_number=sp.port_number,
                                protocol=sp.protocol,
                                old_service=ep.service_name,
                                new_service=sp.service_name,
                                old_version=ep.service_version,
                                new_version=sp.service_version,
                                old_state=ep.state,
                                new_state=sp.state,
                                change_type="modified",
                            ))

                for key, ep in existing_map.items():
                    if key not in scanned_map and ep.state == "open":
                        port_changes.append(DiffHostPortChange(
                            port_number=ep.port_number,
                            protocol=ep.protocol,
                            old_service=ep.service_name,
                            old_version=ep.service_version,
                            old_state=ep.state,
                            new_state="closed",
                            change_type="removed",
                        ))

            changed_hosts.append(DiffChangedHost(
                ip_address=ip,
                mac_address=first.mac_address,
                hostname=first.hostname,
                os_info=first.os_info,
                matched_asset_id=matched_asset_id,
                matched_asset_no=matched_asset_no,
                port_changes=port_changes,
                current_ports=current_ports,
                scan_ports=scan_ports,
            ))

    # MISSING：查找在线资产中未出现在本次扫描的
    from app.schemas.asset import AssetQueryParams
    all_online_params = AssetQueryParams(page=1, page_size=100000, status="online")
    online_assets, _ = asset_repo.list_assets(db, all_online_params)
    scanned_ips = set(hosts_by_ip.keys())

    for asset in online_assets:
        if asset.ip_address not in scanned_ips:
            missing_hosts.append(DiffMissingHost(
                ip_address=asset.ip_address,
                mac_address=asset.mac_address,
                hostname=asset.hostname,
                matched_asset_id=asset.id,
                matched_asset_no=asset.asset_no,
                missing_count=asset.missing_count or 0,
            ))

    return ScanDiffResponse(
        batch_id=batch.id,
        batch_name=batch.batch_name,
        status=batch.status,
        total_hosts=batch.total_hosts or 0,
        new_count=len(new_hosts),
        changed_count=len(changed_hosts),
        missing_count=len(missing_hosts),
        new_hosts=new_hosts,
        changed_hosts=changed_hosts,
        missing_hosts=missing_hosts,
    )


def list_batches(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[ScanBatch], int]:
    from sqlalchemy import func, select
    count = db.scalar(select(func.count()).select_from(ScanBatch)) or 0
    stmt = (
        select(ScanBatch)
        .order_by(ScanBatch.uploaded_at.desc())
        .offset(skip)
        .limit(limit)
    )
    batches = list(db.scalars(stmt).all())
    return batches, count


def confirm_batch(
    db: Session,
    batch_id: int,
    new_assets_data: list[dict] | None = None,
) -> ScanBatch:
    """
    确认导入批次：
    - 新发现资产入库
    - 变更资产更新端口
    - MISSING 资产 missing_count + 1
    - RESTORED 资产 missing_count 归零
    """
    batch = get_batch(db, batch_id)
    if batch.status != "pending":
        raise ValidationError(f"批次状态为 {batch.status}，无法确认")

    # 获取差异数据（重新解析快照项）
    from sqlalchemy import select
    items = list(db.scalars(
        select(ScanSnapshotItem).where(ScanSnapshotItem.scan_batch_id == batch_id)
    ).all())

    # 按 IP 分组
    hosts_by_ip: dict[str, list[ScanSnapshotItem]] = {}
    for item in items:
        hosts_by_ip.setdefault(item.ip_address, []).append(item)

    now = datetime.now(timezone.utc)

    # 处理各类差异
    for ip, host_items in hosts_by_ip.items():
        first = host_items[0]
        diff_type = first.diff_type

        if diff_type == "new":
            # 新资产：需要 new_assets_data 提供补充字段
            # 简化处理：如果没有提供补充数据，跳过
            if new_assets_data:
                asset_data = next(
                    (d for d in new_assets_data if d.get("ip_address") == ip), None
                )
                if asset_data:
                    asset = asset_repo.create_asset(db, **asset_data, source="scan")
                    # 更新端口
                    for item in host_items:
                        if item.port_number is not None:
                            asset_repo.upsert_port(
                                db, asset.id,
                                item.port_number, item.protocol or "tcp",
                                item.service_name, item.service_version,
                            )
                    asset.last_seen_at = now
                    asset.last_scan_batch_id = batch.id

        elif diff_type == "changed" or diff_type == "restored":
            # 更新端口
            asset = asset_repo.get_by_ip(db, ip)
            if asset:
                for item in host_items:
                    if item.port_number is not None:
                        asset_repo.upsert_port(
                            db, asset.id,
                            item.port_number, item.protocol or "tcp",
                            item.service_name, item.service_version,
                        )
                asset.last_seen_at = now
                asset.last_scan_batch_id = batch.id
                if diff_type == "restored":
                    asset.missing_count = 0
                    asset.status = "online"

        elif diff_type == "same":
            asset = asset_repo.get_by_ip(db, ip)
            if asset:
                asset.last_seen_at = now
                asset.last_scan_batch_id = batch.id

    # 处理 MISSING：所有在线资产中未出现在本次扫描的
    from app.schemas.asset import AssetQueryParams
    all_online_params = AssetQueryParams(page=1, page_size=100000, status="online")
    online_assets, _ = asset_repo.list_assets(db, all_online_params)
    scanned_ips = set(hosts_by_ip.keys())

    for asset in online_assets:
        if asset.ip_address not in scanned_ips:
            asset.missing_count = (asset.missing_count or 0) + 1
            # 消失保护：从系统配置读取阈值
            from app.services.config_service import get_missing_threshold
            threshold = get_missing_threshold(db)
            if asset.missing_count >= threshold:
                asset.status = "offline"

    batch.status = "confirmed"
    db.commit()

    logger.info("scan batch confirmed", extra={"batch_id": batch.id})
    return batch


def reject_batch(db: Session, batch_id: int) -> None:
    """拒绝并删除批次"""
    batch = get_batch(db, batch_id)
    if batch.status != "pending":
        raise ValidationError(f"批次状态为 {batch.status}，无法拒绝")
    batch.status = "rejected"
    db.commit()
    logger.info("scan batch rejected", extra={"batch_id": batch.id})
