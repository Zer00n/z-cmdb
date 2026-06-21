"""
系统配置路由
GET   /api/config     读取所有配置
PATCH /api/config     修改配置（super_admin）
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, SuperAdminUser
from app.models.config import SystemConfig
from app.services import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])

# 默认配置项
DEFAULT_CONFIGS = {
    "missing_threshold": {"value": "3", "description": "消失保护阈值（连续未扫到次数）"},
    "upload_max_size_mb": {"value": "50", "description": "上传文件大小上限（MB）"},
    "session_timeout_minutes": {"value": "30", "description": "Session 超时时间（分钟）"},
    "asset_no_prefix": {"value": "CMDB", "description": "资产编号前缀"},
    "llm_provider": {"value": "", "description": "LLM 提供方（deepseek/openrouter/ollama）"},
    "llm_api_key": {"value": "", "description": "LLM API Key（加密存储）"},
    "llm_model": {"value": "", "description": "LLM 模型名称"},
    "llm_base_url": {"value": "", "description": "LLM API 地址（Ollama 等自定义地址）"},
    "llm_route_core_to_local": {"value": "true", "description": "核心资产是否路由到本地 LLM"},
    "llm_ollama_model": {"value": "qwen2.5", "description": "本地 Ollama 模型名称（路由到本地时使用）"},
    "llm_cloud_enabled": {"value": "true", "description": "是否允许使用云端 LLM（super_admin 可全局禁用）"},
    # 大屏配置
    "dashboard_refresh_seconds": {"value": "30", "description": "大屏自动刷新间隔（秒）"},
    "dashboard_list_limit": {"value": "50", "description": "大屏各滚动列表返回上限"},
    "dangerous_ports_list": {
        "value": '[21,22,23,135,139,445,1433,1521,2375,3306,3389,5432,5984,6379,8080,8888,9200,11211,27017]',
        "description": "危险端口清单（JSON 数组）",
    },
    "dangerous_zones": {
        'value': '["dmz","office"]',
        "description": "高危区域（JSON 数组，暴露在这些区域的危险端口为 high）",
    },
    "shadow_offline_days": {"value": "30", "description": "长期离线判定天数"},
    "dashboard_default_layout": {"value": "", "description": "大屏全局默认布局 JSON"},
    # V0.4 成本核算
    "feature_cost_accounting_enabled": {"value": "false", "description": "启用资产成本核算（super_admin 可切换，关闭后数据保留）"},
}


def ensure_defaults(db: Session) -> None:
    """确保默认配置项存在"""
    for key, meta in DEFAULT_CONFIGS.items():
        existing = db.get(SystemConfig, key)
        if existing is None:
            cfg = SystemConfig(
                key=key,
                value=meta["value"],
                description=meta["description"],
            )
            db.add(cfg)
    db.flush()


@router.get("")
def get_config(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """读取所有系统配置"""
    ensure_defaults(db)
    db.commit()

    configs = list(db.scalars(select(SystemConfig)).all())
    result = {}
    for cfg in configs:
        # 隐藏敏感字段的值
        value = cfg.value
        if "api_key" in cfg.key and value:
            value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
        result[cfg.key] = {
            "value": value,
            "description": cfg.description,
            "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
        }
    return result


@router.patch("")
def update_config(
    body: dict,
    request: Request,
    current_user: SuperAdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """修改系统配置（super_admin）"""
    from app.core.encryption import encrypt_value

    ensure_defaults(db)

    updated_keys = []
    for key, value in body.items():
        cfg = db.get(SystemConfig, key)
        if cfg is None:
            # 只允许修改已存在的配置项
            continue
        str_value = str(value) if value is not None else ""
        # 敏感字段：跳过掩码值（防止把 **** 当真实值存入）
        if "api_key" in key:
            if "****" in str_value:
                continue  # 掩码值，不更新
            if str_value:
                str_value = encrypt_value(str_value)
        cfg.value = str_value
        cfg.updated_at = datetime.now(timezone.utc)
        cfg.updated_by = current_user.id if current_user else None  # type: ignore[union-attr]
        updated_keys.append(key)

    if updated_keys:
        audit_service.log_from_request(
            db, request, action_type="CONFIG", user=current_user,  # type: ignore[arg-type]
            target_type="system_config",
            details={"updated_keys": updated_keys},
        )

    db.commit()
    return {"message": f"已更新 {len(updated_keys)} 项配置", "updated": updated_keys}
