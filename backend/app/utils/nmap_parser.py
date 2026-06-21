"""
nmap XML parsing module
Uses python-libnmap for parsing, defusedxml for security validation
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
    """Parsed single port information"""
    port_number: int
    protocol: str       # tcp / udp
    state: str          # open / closed / filtered
    service_name: str | None = None
    service_version: str | None = None


@dataclass
class ParsedHost:
    """Parsed single host information"""
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    os_info: str | None = None
    ports: list[ParsedPort] = field(default_factory=list)


@dataclass
class ParsedScan:
    """Parsed complete scan result"""
    scan_started_at: str | None = None
    scan_finished_at: str | None = None
    hosts: list[ParsedHost] = field(default_factory=list)


def validate_nmap_xml(content: bytes) -> None:
    """
    Security validation: use defusedxml to check XML safety (prevent XXE).
    Also verifies the content is in nmap output format.
    """
    try:
        tree = SafeET.fromstring(content)
    except Exception as exc:
        raise NmapParseError(f"XML parsing failed (possibly contains unsafe content): {exc}") from exc

    # Check that root element is nmaprun
    if tree.tag != "nmaprun":
        raise NmapParseError(
            f"Not a valid nmap XML file (root element is '{tree.tag}', expected 'nmaprun')"
        )


def parse_nmap_xml(content: bytes) -> ParsedScan:
    """
    Parse nmap XML content and return structured data.
    Performs security validation first, then uses python-libnmap to parse.
    """
    # Security validation
    validate_nmap_xml(content)

    # Parse using python-libnmap
    try:
        xml_str = content.decode("utf-8")
        report = NmapParser.parse_fromstring(xml_str)
    except Exception as exc:
        raise NmapParseError(f"nmap XML parsing failed: {exc}") from exc

    result = ParsedScan(
        scan_started_at=report.started if hasattr(report, 'started') else None,
        scan_finished_at=report.endtime if hasattr(report, 'endtime') else None,
    )

    for host in report.hosts:
        if not host.is_up():
            continue

        # IP address
        ip = host.address
        if not ip:
            continue

        parsed_host = ParsedHost(ip_address=ip)

        # MAC address
        if hasattr(host, 'mac') and host.mac:
            parsed_host.mac_address = host.mac

        # Hostname
        if host.hostnames:
            parsed_host.hostname = host.hostnames[0]

        # Operating system
        if host.os_fingerprinted and host.os.osmatches:
            parsed_host.os_info = host.os.osmatches[0].name

        # Ports
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
    """Parse nmap XML from a file path"""
    content = file_path.read_bytes()
    return parse_nmap_xml(content)
