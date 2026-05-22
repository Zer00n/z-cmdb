"""
应用服务清单业务逻辑
"""
import csv
import io
import logging

from sqlalchemy.orm import Session

from app.models.asset_app import AssetApp
from app.repositories import asset_app_repo, asset_repo
from app.schemas.asset_app import (
    AssetAppCreate,
    AssetAppListResponse,
    AssetAppRead,
    AssetAppUpdate,
    AppSearchResponse,
    AppSearchItem,
)

logger = logging.getLogger(__name__)


def list_apps(db: Session, asset_id: int) -> AssetAppListResponse:
    """列出某资产的所有应用"""
    # 确认资产存在
    asset_repo.get_by_id(db, asset_id)
    apps = asset_app_repo.list_by_asset(db, asset_id)
    return AssetAppListResponse(
        items=[AssetAppRead.model_validate(a) for a in apps],
        total=len(apps),
    )


def create_app(db: Session, asset_id: int, data: AssetAppCreate, created_by: int | None = None) -> AssetAppRead:
    """新增应用，若填写了端口则同步写入 asset_ports"""
    # 确认资产存在
    asset_repo.get_by_id(db, asset_id)
    app = asset_app_repo.create(
        db,
        asset_id=asset_id,
        created_by=created_by,
        name=data.name,
        version=data.version,
        category=data.category,
        port=data.port,
        protocol=data.protocol,
        install_path=data.install_path,
        config_path=data.config_path,
        notes=data.notes,
    )
    # 同步端口：若应用填写了端口，写入 asset_ports 表
    if data.port:
        asset_repo.upsert_port(
            db,
            asset_id=asset_id,
            port_number=data.port,
            protocol=data.protocol or "tcp",
            service_name=data.name,
            service_version=data.version,
            state="open",
        )
    db.commit()
    return AssetAppRead.model_validate(app)


def update_app(db: Session, asset_id: int, app_id: int, data: AssetAppUpdate) -> AssetAppRead:
    """更新应用，若端口有变化则同步更新 asset_ports"""
    # 确认资产存在
    asset_repo.get_by_id(db, asset_id)
    app = asset_app_repo.get_by_id(db, app_id)
    # 确认应用属于该资产
    if app.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"资产 {asset_id} 下不存在应用 {app_id}")

    old_port = app.port
    old_protocol = app.protocol or "tcp"

    update_data = data.model_dump(exclude_none=True)
    asset_app_repo.update(db, app, **update_data)

    new_port = app.port
    new_protocol = app.protocol or "tcp"

    # 同步端口：新端口写入/更新 asset_ports
    if new_port:
        asset_repo.upsert_port(
            db,
            asset_id=asset_id,
            port_number=new_port,
            protocol=new_protocol,
            service_name=app.name,
            service_version=app.version,
            state="open",
        )
    db.commit()
    return AssetAppRead.model_validate(app)


def delete_app(db: Session, asset_id: int, app_id: int) -> None:
    """软删除应用"""
    # 确认资产存在
    asset_repo.get_by_id(db, asset_id)
    app = asset_app_repo.get_by_id(db, app_id)
    # 确认应用属于该资产
    if app.asset_id != asset_id:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"资产 {asset_id} 下不存在应用 {app_id}")

    asset_app_repo.soft_delete(db, app)
    db.commit()


def export_apps_csv(db: Session, asset_id: int) -> str:
    """导出某资产的应用清单为 CSV"""
    asset = asset_repo.get_by_id(db, asset_id)
    apps = asset_app_repo.list_by_asset(db, asset_id)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "应用名称", "版本", "大类", "端口", "协议",
        "安装路径", "配置路径", "备注", "来源", "状态",
        "创建时间", "更新时间",
    ])

    for a in apps:
        writer.writerow([
            a.name, a.version or "", a.category or "",
            a.port or "", a.protocol or "",
            a.install_path or "", a.config_path or "",
            a.notes or "", a.source, a.status,
            a.created_at.isoformat(), a.updated_at.isoformat(),
        ])

    return output.getvalue()


def search_apps(db: Session, q: str) -> AppSearchResponse:
    """全局应用搜索"""
    results = asset_app_repo.search_global(db, q)
    items = [AppSearchItem(**r) for r in results]
    return AppSearchResponse(items=items, total=len(items))


def get_app_names(db: Session) -> list[str]:
    """获取所有应用名（去重，用于 autocomplete）"""
    return asset_app_repo.get_all_names(db)
