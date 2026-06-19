"""
大屏布局持久化接口
阶段一：用 system_configs KV 存储
"""
import json
import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, SuperAdminUser
from app.core.exceptions import PermissionDeniedError
from app.models.config import SystemConfig
from app.services import audit_service, config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# 内置缺省布局（全部面板可见，标准位置）
_BUILTIN_DEFAULT = {
    "panels": [
        {"id": "kpi", "visible": True},
        {"id": "zone_topology", "visible": True},
        {"id": "asset_dist", "visible": True},
        {"id": "port_exposure", "visible": True},
        {"id": "dangerous_ports", "visible": True},
        {"id": "shadow_assets", "visible": True},
        {"id": "asset_changes", "visible": True},
        {"id": "activity", "visible": True},
    ],
    "refreshIntervalSec": 30,
    "filters": {},
    "theme": "dark",
}


def _merge_layout(personal: dict | None, global_default: dict | None) -> dict:
    """按优先级合并：个人 > 全局默认 > 内置缺省"""
    if personal:
        return personal
    if global_default:
        return global_default
    return _BUILTIN_DEFAULT


@router.get("/layout")
def get_layout(
    current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """返回当前用户生效布局（按优先级合并）"""
    personal_key = f"dashboard_layout:user:{current_user.id}"
    personal_raw = config_service.get_config_value(db, personal_key, "")
    global_raw = config_service.get_config_value(db, "dashboard_default_layout", "")

    personal = json.loads(personal_raw) if personal_raw else None
    global_default = json.loads(global_raw) if global_raw else None

    return _merge_layout(personal, global_default)


@router.put("/layout")
def save_layout(
    body: dict,
    request: Request,
    current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """保存当前用户个人布局"""
    personal_key = f"dashboard_layout:user:{current_user.id}"
    cfg = db.get(SystemConfig, personal_key)
    value = json.dumps(body, ensure_ascii=False)

    if cfg is None:
        cfg = SystemConfig(
            key=personal_key,
            value=value,
            description=f"用户 {current_user.id} 的大屏个人布局",
            updated_by=current_user.id,
        )
        db.add(cfg)
    else:
        cfg.value = value
        cfg.updated_by = current_user.id

    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,
        target_type="dashboard_layout", target_id=str(current_user.id),
        details={"action": "save_personal_layout"},
    )
    db.commit()
    return {"message": "布局已保存"}


@router.put("/layout/default")
def save_default_layout(
    body: dict,
    request: Request,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """保存全局默认布局（仅 super_admin）"""
    cfg = db.get(SystemConfig, "dashboard_default_layout")
    value = json.dumps(body, ensure_ascii=False)

    if cfg is None:
        cfg = SystemConfig(
            key="dashboard_default_layout",
            value=value,
            description="大屏全局默认布局",
            updated_by=current_user.id,
        )
        db.add(cfg)
    else:
        cfg.value = value
        cfg.updated_by = current_user.id

    audit_service.log_from_request(
        db, request, action_type="CONFIG", user=current_user,
        target_type="dashboard_layout", target_id="default",
        details={"action": "save_global_default_layout"},
    )
    db.commit()
    return {"message": "全局默认布局已保存"}
