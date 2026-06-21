"""
System configuration routes
GET   /api/config     Read all configurations
PATCH /api/config     Update configuration (super_admin)
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

# Default configuration items
DEFAULT_CONFIGS = {
    "missing_threshold": {"value": "3", "description": "Disappearance protection threshold (consecutive scan misses)"},
    "upload_max_size_mb": {"value": "50", "description": "Max upload file size (MB)"},
    "session_timeout_minutes": {"value": "30", "description": "Session timeout (minutes)"},
    "asset_no_prefix": {"value": "CMDB", "description": "Asset number prefix"},
    "llm_provider": {"value": "", "description": "LLM provider (deepseek/openrouter/ollama)"},
    "llm_api_key": {"value": "", "description": "LLM API Key (stored encrypted)"},
    "llm_model": {"value": "", "description": "LLM model name"},
    "llm_base_url": {"value": "", "description": "LLM API endpoint (for Ollama or custom endpoints)"},
    "llm_route_core_to_local": {"value": "true", "description": "Whether to route core assets to local LLM"},
    "llm_ollama_model": {"value": "qwen2.5", "description": "Local Ollama model name (used when routing to local)"},
    "llm_cloud_enabled": {"value": "true", "description": "Allow cloud LLM usage (super_admin can disable globally)"},
    # Dashboard configuration
    "dashboard_refresh_seconds": {"value": "30", "description": "Dashboard auto-refresh interval (seconds)"},
    "dashboard_list_limit": {"value": "50", "description": "Dashboard scrolling list max items"},
    "dangerous_ports_list": {
        "value": '[21,22,23,135,139,445,1433,1521,2375,3306,3389,5432,5984,6379,8080,8888,9200,11211,27017]',
        "description": "Dangerous port list (JSON array)",
    },
    "dangerous_zones": {
        'value': '["dmz","office"]',
        "description": "High-risk zones (JSON array; dangerous ports exposed in these zones are marked high)",
    },
    "shadow_offline_days": {"value": "30", "description": "Long-term offline threshold (days)"},
    "dashboard_default_layout": {"value": "", "description": "Dashboard global default layout JSON"},
    # V0.4 Cost accounting
    "feature_cost_accounting_enabled": {"value": "false", "description": "Enable asset cost accounting (super_admin can toggle; data is retained when disabled)"},
}


def ensure_defaults(db: Session) -> None:
    """Ensure default configuration items exist"""
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
    """Read all system configurations"""
    ensure_defaults(db)
    db.commit()

    configs = list(db.scalars(select(SystemConfig)).all())
    result = {}
    for cfg in configs:
        # Hide sensitive field values
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
    """Update system configuration (super_admin)"""
    from app.core.encryption import encrypt_value

    ensure_defaults(db)

    updated_keys = []
    for key, value in body.items():
        cfg = db.get(SystemConfig, key)
        if cfg is None:
            # Only allow modifying existing configuration items
            continue
        str_value = str(value) if value is not None else ""
        # Sensitive fields: skip masked values (to avoid storing **** as the real value)
        if "api_key" in key:
            if "****" in str_value:
                continue  # Masked value, skip update
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
    return {"message": f"Updated {len(updated_keys)} configuration items", "updated": updated_keys}
