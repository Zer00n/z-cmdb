"""
资产 CRUD 单元测试
"""
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import AssetNotFoundError, DuplicateError, ValidationError
from app.repositories import asset_repo
from app.schemas.asset import AssetCreate, AssetQueryParams, AssetUpdate
from app.services import asset_service


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def sample_asset_data() -> dict:
    return {
        "ip_address": "192.168.1.100",
        "asset_type": "virtual",
        "location": "北京机房-A区-01",
        "owner": "张三",
        "business_system": "订单系统",
        "importance": "core",
        "network_zone": "intranet",
    }


@pytest.fixture
def created_asset(db: Session, sample_asset_data: dict):
    data = AssetCreate(**sample_asset_data)
    return asset_service.create_asset(db, data)


# ── 资产编号生成 ──────────────────────────────────────────────

def test_generate_asset_no(db: Session):
    no1 = asset_repo.generate_asset_no(db)
    assert no1.startswith("CMDB-")
    assert len(no1.split("-")) == 3


def test_generate_asset_no_sequential(db: Session, sample_asset_data: dict):
    """连续创建两个资产，编号应递增"""
    data = AssetCreate(**sample_asset_data)
    a1 = asset_service.create_asset(db, data)

    data2 = AssetCreate(**{**sample_asset_data, "ip_address": "192.168.1.101"})
    a2 = asset_service.create_asset(db, data2)

    seq1 = int(a1.asset_no.split("-")[-1])
    seq2 = int(a2.asset_no.split("-")[-1])
    assert seq2 == seq1 + 1


# ── 创建资产 ──────────────────────────────────────────────────

def test_create_asset_success(db: Session, sample_asset_data: dict):
    data = AssetCreate(**sample_asset_data)
    asset = asset_service.create_asset(db, data)
    assert asset.id is not None
    assert asset.ip_address == "192.168.1.100"
    assert asset.status == "online"
    assert asset.source == "manual"


def test_create_asset_with_custom_no(db: Session, sample_asset_data: dict):
    data = AssetCreate(**{**sample_asset_data, "asset_no": "CUSTOM-001"})
    asset = asset_service.create_asset(db, data)
    assert asset.asset_no == "CUSTOM-001"


def test_create_asset_duplicate_no(db: Session, sample_asset_data: dict):
    data = AssetCreate(**{**sample_asset_data, "asset_no": "DUP-001"})
    asset_service.create_asset(db, data)
    with pytest.raises(DuplicateError):
        data2 = AssetCreate(**{**sample_asset_data, "ip_address": "192.168.1.101", "asset_no": "DUP-001"})
        asset_service.create_asset(db, data2)


def test_create_asset_invalid_ip(db: Session, sample_asset_data: dict):
    from pydantic import ValidationError as PydanticValidationError
    with pytest.raises(PydanticValidationError):
        AssetCreate(**{**sample_asset_data, "ip_address": "999.999.999.999"})


# ── 查询资产 ──────────────────────────────────────────────────

def test_get_asset_success(db: Session, created_asset):
    asset = asset_service.get_asset(db, created_asset.id)
    assert asset.id == created_asset.id


def test_get_asset_not_found(db: Session):
    with pytest.raises(AssetNotFoundError):
        asset_service.get_asset(db, 99999)


def test_list_assets_empty(db: Session):
    params = AssetQueryParams()
    result = asset_service.list_assets(db, params)
    assert result.total == 0
    assert result.items == []


def test_list_assets_with_data(db: Session, sample_asset_data: dict):
    for i in range(3):
        data = AssetCreate(**{**sample_asset_data, "ip_address": f"192.168.1.{100+i}"})
        asset_service.create_asset(db, data)

    params = AssetQueryParams()
    result = asset_service.list_assets(db, params)
    assert result.total == 3
    assert len(result.items) == 3


def test_list_assets_search(db: Session, sample_asset_data: dict):
    data1 = AssetCreate(**{**sample_asset_data, "ip_address": "10.0.0.1", "hostname": "web-prod-01"})
    data2 = AssetCreate(**{**sample_asset_data, "ip_address": "10.0.0.2", "hostname": "db-prod-01"})
    asset_service.create_asset(db, data1)
    asset_service.create_asset(db, data2)

    params = AssetQueryParams(search="web")
    result = asset_service.list_assets(db, params)
    assert result.total == 1
    assert result.items[0].hostname == "web-prod-01"


def test_list_assets_filter_zone(db: Session, sample_asset_data: dict):
    data1 = AssetCreate(**{**sample_asset_data, "ip_address": "10.0.0.1", "network_zone": "dmz"})
    data2 = AssetCreate(**{**sample_asset_data, "ip_address": "10.0.0.2", "network_zone": "intranet"})
    asset_service.create_asset(db, data1)
    asset_service.create_asset(db, data2)

    params = AssetQueryParams(network_zone="dmz")
    result = asset_service.list_assets(db, params)
    assert result.total == 1
    assert result.items[0].network_zone == "dmz"


def test_list_assets_pagination(db: Session, sample_asset_data: dict):
    for i in range(5):
        data = AssetCreate(**{**sample_asset_data, "ip_address": f"192.168.1.{100+i}"})
        asset_service.create_asset(db, data)

    params = AssetQueryParams(page=1, page_size=2)
    result = asset_service.list_assets(db, params)
    assert len(result.items) == 2
    assert result.total == 5
    assert result.total_pages == 3


# ── 更新资产 ──────────────────────────────────────────────────

def test_update_asset_success(db: Session, created_asset):
    update = AssetUpdate(owner="李四", importance="important")
    updated = asset_service.update_asset(db, created_asset.id, update)
    assert updated.owner == "李四"
    assert updated.importance == "important"


def test_update_asset_not_found(db: Session):
    with pytest.raises(AssetNotFoundError):
        asset_service.update_asset(db, 99999, AssetUpdate(owner="李四"))


# ── 下线资产 ──────────────────────────────────────────────────

def test_decommission_asset(db: Session, created_asset):
    asset_service.decommission_asset(db, created_asset.id)
    asset = asset_repo.get_by_id(db, created_asset.id)
    assert asset.status == "decommissioned"


def test_decommission_already_decommissioned(db: Session, created_asset):
    asset_service.decommission_asset(db, created_asset.id)
    with pytest.raises(ValidationError):
        asset_service.decommission_asset(db, created_asset.id)


# ── CSV 导出 ──────────────────────────────────────────────────

def test_export_csv(db: Session, sample_asset_data: dict):
    data = AssetCreate(**sample_asset_data)
    asset_service.create_asset(db, data)

    params = AssetQueryParams()
    csv_content = asset_service.export_assets_csv(db, params)
    lines = csv_content.strip().split("\n")
    assert len(lines) == 2  # 表头 + 1 行数据
    assert "资产编号" in lines[0]


# ── HTTP 接口测试 ─────────────────────────────────────────────

def test_create_asset_api(client, db_from_client):
    """POST /api/assets 需要 admin token"""
    from app.core.security import hash_password, create_access_token
    from app.repositories import user_repo

    # 创建 admin 用户并获取 token
    pwd_hash = hash_password("Admin@2026Test")
    user = user_repo.create_user(db_from_client, "apiadmin", pwd_hash, "admin")
    db_from_client.commit()
    token = create_access_token(user.id, user.role)

    resp = client.post(
        "/api/assets",
        json={
            "ip_address": "192.168.1.200",
            "asset_type": "virtual",
            "location": "北京机房",
            "owner": "测试员",
            "business_system": "测试系统",
            "importance": "normal",
            "network_zone": "intranet",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["ip_address"] == "192.168.1.200"
    assert data["asset_no"].startswith("CMDB-")


def test_list_assets_api(client, db_from_client):
    """GET /api/assets 需要登录"""
    from app.core.security import hash_password, create_access_token
    from app.repositories import user_repo

    pwd_hash = hash_password("Admin@2026Test")
    user = user_repo.create_user(db_from_client, "listuser", pwd_hash, "admin")
    db_from_client.commit()
    token = create_access_token(user.id, user.role)

    resp = client.get("/api/assets", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_list_assets_api_requires_auth(client):
    """未认证返回 401"""
    resp = client.get("/api/assets")
    assert resp.status_code == 401
