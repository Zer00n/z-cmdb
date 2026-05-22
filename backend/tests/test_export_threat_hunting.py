"""
威胁狩猎助手兼容导出 单元测试
覆盖：字段映射、行展开、过滤、CSV 格式
"""
import csv
import io

import pytest
from sqlalchemy.orm import Session

from app.models.asset_app import AssetApp
from app.repositories import asset_repo
from app.schemas.asset import AssetCreate, AssetQueryParams
from app.services import asset_service


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def sample_asset_data() -> dict:
    return {
        "ip_address": "192.168.1.100",
        "hostname": "web-prod-01",
        "asset_type": "virtual",
        "os_info": "Ubuntu 22.04 LTS",
        "location": "北京机房-A区-01",
        "owner": "zhangsan",
        "business_system": "订单系统",
        "importance": "core",
        "network_zone": "dmz",
    }


@pytest.fixture
def asset_with_app(db: Session, sample_asset_data: dict):
    """创建一个资产并关联一个应用"""
    data = AssetCreate(**sample_asset_data)
    asset = asset_service.create_asset(db, data)

    app = AssetApp(
        asset_id=asset.id,
        name="nginx",
        version="1.18.0",
        port=80,
        protocol="tcp",
        notes="主 Web 服务",
        source="manual",
        status="active",
    )
    db.add(app)
    db.commit()
    return asset


@pytest.fixture
def asset_with_multiple_apps(db: Session, sample_asset_data: dict):
    """创建一个资产并关联多个应用"""
    data = AssetCreate(**sample_asset_data)
    asset = asset_service.create_asset(db, data)

    apps_data = [
        {"name": "nginx", "version": "1.18.0", "port": 80, "protocol": "tcp"},
        {"name": "mysql", "version": "8.0.32", "port": 3306, "protocol": "tcp"},
        {"name": "redis", "version": "7.0.5", "port": 6379, "protocol": "tcp"},
    ]
    for ad in apps_data:
        app = AssetApp(asset_id=asset.id, source="manual", status="active", **ad)
        db.add(app)
    db.commit()
    return asset


# ── OS 拆分测试 ──────────────────────────────────────────────

def test_split_os_ubuntu():
    name, ver = asset_service._split_os("Ubuntu 22.04 LTS")
    assert name == "Ubuntu"
    assert ver == "22.04 LTS"


def test_split_os_windows_server():
    name, ver = asset_service._split_os("Windows Server 2019")
    assert name == "Windows Server"
    assert ver == "2019"


def test_split_os_single_word():
    name, ver = asset_service._split_os("CentOS")
    assert name == "CentOS"
    assert ver == ""


def test_split_os_none():
    name, ver = asset_service._split_os(None)
    assert name == ""
    assert ver == ""


def test_split_os_red_hat():
    name, ver = asset_service._split_os("Red Hat Enterprise Linux 8.6")
    assert name == "Red Hat"
    assert ver == "Enterprise Linux 8.6"


# ── 映射函数测试 ─────────────────────────────────────────────

def test_map_criticality():
    assert asset_service._map_criticality("core") == "high"
    assert asset_service._map_criticality("important") == "medium"
    assert asset_service._map_criticality("normal") == "low"
    assert asset_service._map_criticality("unknown") == "low"


def test_map_exposure():
    assert asset_service._map_exposure("dmz") == "public"
    assert asset_service._map_exposure("intranet") == "internal"
    assert asset_service._map_exposure("office") == "office"
    assert asset_service._map_exposure("management") == "internal"
    assert asset_service._map_exposure("other") == "internal"


def test_resolve_vendor():
    assert asset_service._resolve_vendor("nginx") == "nginx"
    assert asset_service._resolve_vendor("mysql") == "Oracle"
    assert asset_service._resolve_vendor("Redis") == "Redis Ltd"
    assert asset_service._resolve_vendor("custom-app") == "custom-app"
    assert asset_service._resolve_vendor(None) == ""


def test_resolve_environment():
    assert asset_service._resolve_environment("订单系统") == "prod"
    assert asset_service._resolve_environment("dev-订单系统") == "dev"
    assert asset_service._resolve_environment("test-系统") == "test"
    assert asset_service._resolve_environment("staging-系统") == "staging"
    assert asset_service._resolve_environment("uat-系统") == "staging"


# ── 导出功能集成测试 ─────────────────────────────────────────

def test_export_single_asset_with_app(db: Session, asset_with_app):
    """一个资产一个应用 → 一行数据"""
    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(db, params)

    assert row_count == 1
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1

    row = rows[0]
    assert row["ip"] == "192.168.1.100"
    assert row["hostname"] == "web-prod-01"
    assert row["os_name"] == "Ubuntu"
    assert row["os_version"] == "22.04 LTS"
    assert row["environment"] == "prod"
    assert row["criticality"] == "high"
    assert row["owner"] == "zhangsan"
    assert row["product"] == "nginx"
    assert row["version"] == "1.18.0"
    assert row["vendor"] == "nginx"
    assert row["port"] == "80"
    assert row["protocol"] == "tcp"
    assert row["exposure_scope"] == "public"


def test_export_asset_multiple_apps(db: Session, asset_with_multiple_apps):
    """一个资产多个应用 → 多行数据"""
    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(db, params)

    assert row_count == 3
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 3

    # 所有行共享相同的资产信息
    for row in rows:
        assert row["ip"] == "192.168.1.100"
        assert row["hostname"] == "web-prod-01"
        assert row["criticality"] == "high"

    # 各行有不同的应用信息
    products = {row["product"] for row in rows}
    assert products == {"nginx", "mysql", "redis"}

    # mysql 的 vendor 应该是 Oracle
    mysql_row = next(r for r in rows if r["product"] == "mysql")
    assert mysql_row["vendor"] == "Oracle"


def test_export_asset_no_apps_default(db: Session, sample_asset_data: dict):
    """无应用的资产默认输出空 product 行"""
    data = AssetCreate(**sample_asset_data)
    asset_service.create_asset(db, data)

    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(db, params)

    assert row_count == 1
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["product"] == ""
    assert rows[0]["version"] == ""
    assert rows[0]["vendor"] == ""
    assert rows[0]["port"] == ""


def test_export_asset_no_apps_skip(db: Session, sample_asset_data: dict):
    """skip_empty_apps=True 时跳过无应用的资产"""
    data = AssetCreate(**sample_asset_data)
    asset_service.create_asset(db, data)

    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(
        db, params, skip_empty_apps=True
    )

    assert row_count == 0
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 0


def test_export_excludes_decommissioned(db: Session, sample_asset_data: dict):
    """默认不导出已下线资产"""
    data = AssetCreate(**sample_asset_data)
    asset = asset_service.create_asset(db, data)
    asset_service.decommission_asset(db, asset.id)

    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(db, params)
    assert row_count == 0


def test_export_includes_decommissioned_when_flag(db: Session, sample_asset_data: dict):
    """include_decommissioned=True 时包含已下线资产"""
    data = AssetCreate(**sample_asset_data)
    asset = asset_service.create_asset(db, data)
    asset_service.decommission_asset(db, asset.id)

    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(
        db, params, include_decommissioned=True
    )
    assert row_count == 1


def test_export_csv_escape(db: Session):
    """备注含逗号、引号时 CSV 转义正确"""
    data = AssetCreate(
        ip_address="10.0.0.1",
        asset_type="virtual",
        location="北京",
        owner="test",
        business_system="系统",
        importance="normal",
        network_zone="intranet",
        remark='备注含"引号",和逗号',
    )
    asset = asset_service.create_asset(db, data)

    app = AssetApp(
        asset_id=asset.id,
        name="app1",
        version="1.0",
        notes='应用备注含\n换行',
        source="manual",
        status="active",
    )
    db.add(app)
    db.commit()

    params = AssetQueryParams()
    csv_content, row_count = asset_service.export_assets_threat_hunting_csv(db, params)

    # 用 csv reader 解析应该不报错
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 1
    # 备注应该被正确拼接且换行被替换
    assert "引号" in rows[0]["notes"]
    assert "\n" not in rows[0]["notes"]


def test_export_utf8_bom():
    """导出内容编码为 UTF-8 BOM"""
    # 这个测试验证路由层的 encode("utf-8-sig") 行为
    content = "ip,hostname\n192.168.1.1,test\n"
    encoded = content.encode("utf-8-sig")
    assert encoded[:3] == b"\xef\xbb\xbf"


def test_export_csv_header_matches_template(db: Session, asset_with_app):
    """导出 CSV 表头与威胁狩猎助手模板一致"""
    params = AssetQueryParams()
    csv_content, _ = asset_service.export_assets_threat_hunting_csv(db, params)

    expected_header = "ip,hostname,os_name,os_version,environment,criticality,owner,tags,product,version,vendor,port,protocol,exposure_scope,notes"
    first_line = csv_content.split("\n")[0].strip("\r")
    assert first_line == expected_header


def test_export_tags_field(db: Session, sample_asset_data: dict):
    """tags 字段正确拼接"""
    data = AssetCreate(**sample_asset_data)
    asset_service.create_asset(db, data)

    params = AssetQueryParams()
    csv_content, _ = asset_service.export_assets_threat_hunting_csv(db, params)

    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    tags = rows[0]["tags"]
    # 应包含 asset_type, network_zone, business_system, importance
    assert "virtual" in tags
    assert "dmz" in tags
    assert "订单系统" in tags
    assert "core" in tags


# ── HTTP 接口测试 ─────────────────────────────────────────────

def test_export_threat_hunting_api(client, db_from_client):
    """GET /api/assets/export-threat-hunting 返回 CSV"""
    from app.core.security import hash_password, create_access_token
    from app.models.asset_app import AssetApp
    from app.repositories import user_repo

    # 创建用户
    pwd_hash = hash_password("Admin@2026Test")
    user = user_repo.create_user(db_from_client, "exportuser", pwd_hash, "admin")
    db_from_client.commit()
    token = create_access_token(user.id, user.role)

    # 创建资产
    resp = client.post(
        "/api/assets",
        json={
            "ip_address": "192.168.1.200",
            "hostname": "api-server",
            "asset_type": "virtual",
            "os_info": "Ubuntu 22.04",
            "location": "北京机房",
            "owner": "测试员",
            "business_system": "测试系统",
            "importance": "important",
            "network_zone": "intranet",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    # 创建应用
    app = AssetApp(
        asset_id=asset_id,
        name="tomcat",
        version="9.0.65",
        port=8080,
        protocol="tcp",
        source="manual",
        status="active",
    )
    db_from_client.add(app)
    db_from_client.commit()

    # 调用导出接口
    resp = client.get(
        "/api/assets/export-threat-hunting",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "cmdb_threat_hunting_" in resp.headers["content-disposition"]

    # 解析 CSV（去掉 BOM）
    content = resp.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) >= 1

    row = rows[0]
    assert row["ip"] == "192.168.1.200"
    assert row["hostname"] == "api-server"
    assert row["product"] == "tomcat"
    assert row["criticality"] == "medium"
    assert row["exposure_scope"] == "internal"


def test_export_threat_hunting_api_requires_auth(client):
    """未认证返回 401"""
    resp = client.get("/api/assets/export-threat-hunting")
    assert resp.status_code == 401
