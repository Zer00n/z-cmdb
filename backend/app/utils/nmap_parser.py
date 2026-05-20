"""
nmap XML 解析模块
使用 python-libnmap 解析，defusedxml 做安全校验
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

from defusedxml import ElementTree as SafeET
from libnmap.parser import NmapParser

from app.core.exceptions import NmapParseError

logger = logging.getLogger(__name__)


@dataclass
class ParsedPort:
    """解析出的单个端口信息"""
    port_number: int
    protocol: str       # tcp / udp
    state: str          # open / closed / filtered
    service_name: str | None = None
    service_version: str | None = None


@dataclass
class ParsedHost:
    """解析出的单个主机信息"""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    os_info: str | None = None
    ports: list[ParsedPort] = field(default_factory=list)


@dataclass
class ParsedScan:
    """解析出的完整扫描结果"""
    scan_started_at: str | None = None
    scan_finished_at: str | None = None
    hosts: list[ParsedHost] = field(default_factory=list)


def validate_nmap_xml(content: bytes) -> None:
    """
    安全校验：使用 defusedxml 检查 XML 是否安全（防 XXE）。
    同时验证是否为 nmap 输出格式。
    """
    try:
        tree = SafeET.fromstring(content)
    except Exception as exc:
        raise NmapParseError(f"XML 解析失败（可能包含不安全内容）: {exc}") from exc

    # 检查根元素是否为 nmaprun
    if tree.tag != "nmaprun":
        raise NmapParseError(
            f"不是有效的 nmap XML 文件（根元素为 '{tree.tag}'，期望 'nmaprun'）"
        )


def parse_nmap_xml(content: bytes) -> ParsedScan:
    """
    解析 nmap XML 内容，返回结构化数据。
    先做安全校验，再用 python-libnmap 解析。
    """
    # 安全校验
    validate_nmap_xml(content)

    # 使用 python-libnmap 解析
    try:
        xml_str = content.decode("utf-8")
        report = NmapParser.parse_fromstring(xml_str)
    except Exception as exc:
        raise NmapParseError(f"nmap XML 解析失败: {exc}") from exc

    result = ParsedScan(
        scan_started_at=report.started if hasattr(report, 'started') else None,
        scan_finished_at=report.endtime if hasattr(report, 'endtime') else None,
    )

    for host in report.hosts:
        if not host.is_up():
            continue

        # IP 地址
        ip = host.address
        if not ip:
            continue

        parsed_host = ParsedHost(ip_address=ip)

        # MAC 地址
        if hasattr(host, 'mac') and host.mac:
            parsed_host.mac_address = host.mac

        # 主机名
        if host.hostnames:
            parsed_host.hostname = host.hostnames[0]

        # 操作系统
        if host.os_fingerprinted and host.os.osmatches:
            parsed_host.os_info = host.os.osmatches[0].name

        # 端口
        for svc in host.services:
            port = ParsedPort(
                port_number=svc.port,
                protocol=svc.protocol,
                state=svc.state,
                service_name=svc.service if svc.service else None,
                service_version=svc.banner if svc.banner else None,
            )
            parsed_host.ports.append(port)

        result.hosts.append(parsed_host)

    logger.info(
        "nmap xml parsed",
        extra={"host_count": len(result.hosts)},
    )
    return result


def parse_nmap_file(file_path: Path) -> ParsedScan:
    """从文件路径解析 nmap XML"""
    content = file_path.read_bytes()
    return parse_nmap_xml(content)
