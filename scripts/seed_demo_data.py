"""
为资产总览页面填充示例资产数据。
用法：cd backend && python scripts/seed_demo_data.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.asset import Asset, AssetPort
from app.models.user import User
from app.repositories import user_repo


def main():
    db = SessionLocal()
    try:
        existing = db.query(Asset).count()
        if existing > 0:
            print(f"数据库已有 {existing} 个资产，跳过填充。")
            return

        print("正在填充示例资产数据...")

        assets_data = [
            # (asset_no, ip, hostname, type, os, location, owner, biz, importance, zone, ports)
            ("CMDB-0001", "192.168.1.10", "web-prod-01", "physical", "CentOS 7.9", "IDC-A机房", "张三", "电商系统", "core", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (80, "tcp", "http", "nginx 1.20"), (443, "tcp", "https", "nginx 1.20")]),
            ("CMDB-0002", "192.168.1.11", "web-prod-02", "physical", "CentOS 7.9", "IDC-A机房", "张三", "电商系统", "core", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (80, "tcp", "http", "nginx 1.20"), (443, "tcp", "https", "nginx 1.20")]),
            ("CMDB-0003", "192.168.1.20", "db-prod-01", "physical", "CentOS 7.9", "IDC-A机房", "李四", "电商系统", "core", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (3306, "tcp", "mysql", "MySQL 8.0.28")]),
            ("CMDB-0004", "192.168.1.21", "db-prod-02", "physical", "CentOS 7.9", "IDC-A机房", "李四", "电商系统", "core", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (3306, "tcp", "mysql", "MySQL 8.0.28")]),
            ("CMDB-0005", "192.168.1.30", "redis-prod-01", "physical", "Ubuntu 22.04", "IDC-A机房", "李四", "电商系统", "important", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.9"), (6379, "tcp", "redis", "Redis 7.0.5")]),
            ("CMDB-0006", "10.0.1.10", "dmz-nginx-01", "physical", "CentOS 8", "IDC-B机房", "王五", "反向代理", "important", "dmz",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (80, "tcp", "http", "nginx 1.24"), (443, "tcp", "https", "nginx 1.24"), (8080, "tcp", "http-proxy", "nginx 1.24")]),
            ("CMDB-0007", "10.0.1.11", "dmz-waf-01", "physical", "CentOS 8", "IDC-B机房", "王五", "WAF", "important", "dmz",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (443, "tcp", "https", "WAF 3.2")]),
            ("CMDB-0008", "172.16.0.10", "office-dc-01", "physical", "Windows Server 2019", "办公楼", "赵六", "AD域控", "core", "office",
             [(135, "tcp", "msrpc", ""), (139, "tcp", "netbios-ssn", ""), (389, "tcp", "ldap", ""), (445, "tcp", "microsoft-ds", ""), (3389, "tcp", "ms-wbt-server", "")]),
            ("CMDB-0009", "172.16.0.20", "office-file-01", "physical", "Windows Server 2019", "办公楼", "赵六", "文件服务器", "normal", "office",
             [(135, "tcp", "msrpc", ""), (445, "tcp", "microsoft-ds", ""), (3389, "tcp", "ms-wbt-server", "")]),
            ("CMDB-0010", "192.168.1.50", "k8s-master-01", "virtual", "Ubuntu 22.04", "IDC-A机房", "张三", "容器平台", "core", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.9"), (6443, "tcp", "kubernetes-api", ""), (10250, "tcp", "kubelet", "")]),
            ("CMDB-0011", "192.168.1.51", "k8s-node-01", "virtual", "Ubuntu 22.04", "IDC-A机房", "张三", "容器平台", "important", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.9"), (10250, "tcp", "kubelet", "")]),
            ("CMDB-0012", "192.168.1.52", "k8s-node-02", "virtual", "Ubuntu 22.04", "IDC-A机房", "张三", "容器平台", "important", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.9"), (10250, "tcp", "kubelet", "")]),
            ("CMDB-0013", "192.168.1.60", "gitlab-01", "virtual", "CentOS 8", "IDC-A机房", "孙七", "代码仓库", "important", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (80, "tcp", "http", "nginx 1.20"), (443, "tcp", "https", "nginx 1.20")]),
            ("CMDB-0014", "192.168.1.70", "jenkins-01", "virtual", "CentOS 8", "IDC-A机房", "孙七", "CI/CD", "normal", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (8080, "tcp", "http", "Jenkins 2.387")]),
            ("CMDB-0015", "192.168.1.80", "monitor-01", "virtual", "Ubuntu 22.04", "IDC-A机房", "王五", "监控系统", "important", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.9"), (9090, "tcp", "http", "Prometheus 2.45"), (3000, "tcp", "http", "Grafana 10.0")]),
            ("CMDB-0016", "10.0.0.1", "fw-core-01", "network_device", "FortiOS 7.2", "IDC-A机房", "王五", "防火墙", "core", "management",
             [(22, "tcp", "ssh", ""), (443, "tcp", "https", "FortiGate")]),
            ("CMDB-0017", "10.0.0.2", "sw-core-01", "network_device", "Cisco IOS 15.2", "IDC-A机房", "王五", "核心交换机", "core", "management",
             [(22, "tcp", "ssh", ""), (161, "udp", "snmp", "")]),
            ("CMDB-0018", "10.0.0.3", "sw-access-01", "network_device", "Cisco IOS 15.2", "办公楼", "王五", "接入交换机", "normal", "office",
             [(22, "tcp", "ssh", ""), (161, "udp", "snmp", "")]),
            ("CMDB-0019", "47.100.1.100", "aliyun-web-01", "cloud_server", "Alibaba Cloud Linux 3", "阿里云华东1", "张三", "电商系统", "important", "aliyun",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (80, "tcp", "http", "nginx 1.24"), (443, "tcp", "https", "nginx 1.24")]),
            ("CMDB-0020", "47.100.1.101", "aliyun-api-01", "cloud_server", "Alibaba Cloud Linux 3", "阿里云华东1", "张三", "API网关", "important", "aliyun",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (8080, "tcp", "http", "Kong 3.2")]),
            ("CMDB-0021", "192.168.1.200", "test-app-01", "virtual", "Ubuntu 22.04", "IDC-A机房", "孙七", "测试环境", "normal", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.9"), (3000, "tcp", "http", "Node.js 18")]),
            ("CMDB-0022", "192.168.1.201", "test-db-01", "virtual", "CentOS 8", "IDC-A机房", "孙七", "测试环境", "normal", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (5432, "tcp", "postgresql", "PostgreSQL 15.2")]),
            ("CMDB-0023", "192.168.1.90", "jumpserver-01", "physical", "CentOS 8", "IDC-A机房", "王五", "堡垒机", "important", "management",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (443, "tcp", "https", "JumpServer 3.10")]),
            ("CMDB-0024", "10.0.2.10", "vpn-gateway", "network_device", "OpenVPN 2.6", "IDC-A机房", "王五", "VPN网关", "important", "management",
             [(22, "tcp", "ssh", ""), (1194, "udp", "openvpn", "OpenVPN 2.6")]),
            ("CMDB-0025", "192.168.1.95", "nacos-01", "virtual", "CentOS 8", "IDC-A机房", "张三", "注册中心", "core", "intranet",
             [(22, "tcp", "ssh", "OpenSSH 8.0"), (8848, "tcp", "http", "Nacos 2.2"), (9848, "tcp", "grpc", "Nacos 2.2")]),
        ]

        now = datetime.now(timezone.utc)
        for asset_no, ip, hostname, a_type, os_info, location, owner, biz, importance, zone, ports in assets_data:
            asset = Asset(
                asset_no=asset_no,
                ip_address=ip,
                hostname=hostname,
                asset_type=a_type,
                os_info=os_info,
                location=location,
                owner=owner,
                business_system=biz,
                importance=importance,
                network_zone=zone,
                status="online",
                source="manual",
                last_seen_at=now,
            )
            db.add(asset)
            db.flush()

            for port_num, proto, svc, ver in ports:
                port = AssetPort(
                    asset_id=asset.id,
                    port_number=port_num,
                    protocol=proto,
                    service_name=svc,
                    service_version=ver,
                    state="open",
                    last_seen_at=now,
                )
                db.add(port)

        # 添加一个离线资产
        offline_asset = Asset(
            asset_no="CMDB-0026",
            ip_address="192.168.1.99",
            hostname="old-server-01",
            asset_type="physical",
            os_info="CentOS 6.10",
            location="IDC-A机房",
            owner="",
            business_system="",
            importance="normal",
            network_zone="intranet",
            status="offline",
            source="scan",
            missing_count=5,
        )
        db.add(offline_asset)
        db.flush()

        # 一个缺字段的扫描资产
        shadow_asset = Asset(
            asset_no="CMDB-0027",
            ip_address="10.0.1.50",
            hostname="unknown-device",
            asset_type="other",
            os_info="",
            location="",
            owner="",
            business_system="",
            importance="normal",
            network_zone="dmz",
            status="online",
            source="scan",
            last_seen_at=now,
        )
        db.add(shadow_asset)
        db.flush()

        # 添加一个 auditor 用户（如不存在）
        existing_auditor = db.query(User).filter(User.role == "auditor").first()
        if not existing_auditor:
            auditor = User(
                username="auditor",
                password_hash=hash_password("Auditor@123456"),
                role="auditor",
                full_name="审计员",
                status="active",
            )
            db.add(auditor)

        db.commit()
        print(f"已填充 {len(assets_data) + 2} 个示例资产（含 1 个离线、1 个影子资产）")
        print("auditor 账号：auditor / Auditor@123456")

    finally:
        db.close()


if __name__ == "__main__":
    main()
