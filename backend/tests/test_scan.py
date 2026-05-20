"""
扫描模块单元测试
覆盖：nmap 解析、差异分析、上传 API
"""
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NmapParseError
from app.models.asset import Asset
from app.repositories import asset_repo
from app.schemas.asset import AssetCreate
from app.services import asset_service
from app.services.diff_service import compute_diff
from app.utils.nmap_parser import ParsedHost, ParsedPort, parse_nmap_xml, validate_nmap_xml


# ── nmap XML 样本 ────────────────────────────────────────────

SAMPLE_NMAP_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" args="nmap -sS -sV -O -oX scan.xml 192.168.1.0/24"
         start="1716000000" startstr="Sat May 18 00:00:00 2026"
         version="7.94" xmloutputversion="1.05">
<host starttime="1716000001" endtime="1716000010">
  <status state="up" reason="arp-response"/>
  <address addr="192.168.1.10" addrtype="ipv4"/>
  <address addr="AA:BB:CC:DD:EE:01" addrtype="mac"/>
  <hostnames><hostname name="web-prod-01" type="PTR"/></hostnames>
  <ports>
    <port protocol="tcp" portid="22">
      <state state="open" reason="syn-ack"/>
      <service name="ssh" product="OpenSSH" version="8.9"/>
    </port>
    <port protocol="tcp" portid="80">
      <state state="open" reason="syn-ack"/>
      <service name="http" product="nginx" version="1.24"/>
    </port>
  </ports>
  <os><osmatch name="Linux 5.x" accuracy="95" line="1"><osclass type="general purpose" vendor="Linux" osfamily="Linux" osgen="5.X" accuracy="95"/></osmatch></os>
</host>
<host starttime="1716000001" endtime="1716000010">
  <status state="up" reason="arp-response"/>
  <address addr="192.168.1.20" addrtype="ipv4"/>
  <address addr="AA:BB:CC:DD:EE:02" addrtype="mac"/>
  <hostnames><hostname name="db-prod-01" type="PTR"/></hostnames>
  <ports>
    <port protocol="tcp" portid="3306">
      <state state="open" reason="syn-ack"/>
      <service name="mysql" product="MySQL" version="8.0"/>
    </port>
  </ports>
</host>
<host starttime="1716000001" endtime="1716000010">
  <status state="down" reason="no-response"/>
  <address addr="192.168.1.30" addrtype="ipv4"/>
</host>
<runstats><finished time="1716000060"/></runstats>
</nmaprun>
"""

INVALID_XML = b"<html><body>not nmap</body></html>"
MALFORMED_XML = b"this is not xml at all"


# ── nmap 解析测试 ─────────────────────────────────────────────

def test_parse_nmap_xml_success():
    result = parse_nmap_xml(SAMPLE_NMAP_XML)
    assert len(result.hosts) == 2  # down 的主机被过滤
    assert result.hosts[0].ip_address == "192.168.1.10"
    assert result.hosts[0].mac_address == "AA:BB:CC:DD:EE:01"
    assert result.hosts[0].hostname == "web-prod-01"
    assert len(result.hosts[0].ports) == 2
    assert result.hosts[0].ports[0].port_number == 22
    assert result.hosts[0].ports[0].service_name == "ssh"


def test_parse_nmap_xml_filters_down_hosts():
    result = parse_nmap_xml(SAMPLE_NMAP_XML)
    ips = [h.ip_address for h in result.hosts]
    assert "192.168.1.30" not in ips


def test_validate_nmap_xml_invalid_root():
    with pytest.raises(NmapParseError, match="不是有效的 nmap XML"):
        validate_nmap_xml(INVALID_XML)


def test_validate_nmap_xml_malformed():
    with pytest.raises(NmapParseError, match="XML 解析失败"):
        validate_nmap_xml(MALFORMED_XML)


# ── 差异分析测试 ──────────────────────────────────────────────

def test_diff_new_host(db: Session):
    """没有匹配资产时应标记为 NEW"""
    hosts = [ParsedHost(ip_address="10.0.0.1", ports=[])]
    summary = compute_diff(db, hosts)
    assert summary.new_count == 1
    assert summary.new_hosts[0].diff_type == "NEW"


def test_diff_same_host(db: Session):
    """匹配到资产且端口无变化时标记为 SAME"""
    # 先创建资产
    data = AssetCreate(
        ip_address="10.0.0.2",
        asset_type="virtual",
        location="测试",
        owner="测试",
        business_system="测试",
        importance="normal",
        network_zone="intranet",
    )
    asset = asset_service.create_asset(db, data)

    hosts = [ParsedHost(ip_address="10.0.0.2", ports=[])]
    summary = compute_diff(db, hosts)
    assert len(summary.same_hosts) == 1
    assert summary.same_hosts[0].matched_asset_id == asset.id


def test_diff_changed_host(db: Session):
    """匹配到资产但端口有变化时标记为 CHANGED"""
    data = AssetCreate(
        ip_address="10.0.0.3",
        asset_type="virtual",
        location="测试",
        owner="测试",
        business_system="测试",
        importance="normal",
        network_zone="intranet",
    )
    asset = asset_service.create_asset(db, data)
    # 给资产添加一个端口
    asset_repo.upsert_port(db, asset.id, 22, "tcp", "ssh", "OpenSSH 8.0")
    db.commit()

    # 扫描发现端口版本变了
    hosts = [ParsedHost(
        ip_address="10.0.0.3",
        ports=[ParsedPort(port_number=22, protocol="tcp", state="open", service_name="ssh", service_version="OpenSSH 9.0")],
    )]
    summary = compute_diff(db, hosts)
    assert summary.changed_count == 1
    assert summary.changed_hosts[0].diff_type == "CHANGED"


def test_diff_missing_host(db: Session):
    """在线资产未被扫到时标记为 MISSING"""
    data = AssetCreate(
        ip_address="10.0.0.4",
        asset_type="virtual",
        location="测试",
        owner="测试",
        business_system="测试",
        importance="normal",
        network_zone="intranet",
    )
    asset_service.create_asset(db, data)

    # 扫描结果为空（没扫到任何主机）
    summary = compute_diff(db, [])
    assert summary.missing_count == 1
    assert summary.missing_assets[0].diff_type == "MISSING"


def test_diff_mac_match_priority(db: Session):
    """MAC 匹配优先于 IP 匹配"""
    data = AssetCreate(
        ip_address="10.0.0.5",
        mac_address="AA:BB:CC:DD:EE:FF",
        asset_type="virtual",
        location="测试",
        owner="测试",
        business_system="测试",
        importance="normal",
        network_zone="intranet",
    )
    asset = asset_service.create_asset(db, data)

    # 扫描发现同一 MAC 但 IP 变了
    hosts = [ParsedHost(
        ip_address="10.0.0.99",  # IP 不同
        mac_address="AA:BB:CC:DD:EE:FF",  # MAC 相同
        ports=[],
    )]
    summary = compute_diff(db, hosts)
    # 应该匹配到已有资产（通过 MAC），不是 NEW
    assert summary.new_count == 0
    assert len(summary.same_hosts) == 1
    assert summary.same_hosts[0].matched_asset_id == asset.id
