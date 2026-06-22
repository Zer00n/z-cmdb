"""
System configuration service
Reads runtime-tunable configuration items from the system_configs table
"""
import json

from sqlalchemy.orm import Session

from app.models.config import SystemConfig


def get_config_value(db: Session, key: str, default: str = "") -> str:
    """Read a config value from system_configs table; returns default if not found"""
    cfg = db.get(SystemConfig, key)
    if cfg is None or cfg.value is None:
        return default
    return cfg.value


def get_config_int(db: Session, key: str, default: int = 0) -> int:
    """Read integer config"""
    val = get_config_value(db, key, str(default))
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_missing_threshold(db: Session) -> int:
    """Missing protection threshold (default 3)"""
    return get_config_int(db, "missing_threshold", 3)


def get_upload_max_size_mb(db: Session) -> int:
    """Upload file size limit in MB (default 50)"""
    return get_config_int(db, "upload_max_size_mb", 50)


def get_asset_no_prefix(db: Session) -> str:
    """Asset number prefix (default CMDB)"""
    return get_config_value(db, "asset_no_prefix", "CMDB")


def has_auditor_user(db: Session) -> bool:
    """Check whether there is at least one active auditor user in the system"""
    from sqlalchemy import select, func
    from app.models.user import User
    count = db.scalar(
        select(func.count()).select_from(User).where(
            User.role == "auditor", User.status == "active"
        )
    ) or 0
    return count > 0


# ── Dashboard Configuration ──────────────────────────────────────────────────

DEFAULT_DANGEROUS_PORTS = [21, 22, 23, 135, 139, 445, 1433, 1521, 2375,
                           3306, 3389, 5432, 5984, 6379, 8080, 8888, 9200, 11211, 27017]
DEFAULT_DANGEROUS_ZONES = ["dmz", "office"]


def get_dashboard_refresh_seconds(db: Session) -> int:
    """Dashboard auto-refresh interval (default 30 seconds)"""
    return get_config_int(db, "dashboard_refresh_seconds", 30)


def get_dashboard_list_limit(db: Session) -> int:
    """Dashboard scrolling list return limit (default 50)"""
    return get_config_int(db, "dashboard_list_limit", 50)


def get_dangerous_ports_list(db: Session) -> set[int]:
    """Dangerous ports list, read from JSON config with built-in defaults as fallback"""
    raw = get_config_value(db, "dangerous_ports_list", "")
    if raw:
        try:
            return set(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            pass
    return set(DEFAULT_DANGEROUS_PORTS)


def get_dangerous_zones(db: Session) -> set[str]:
    """High-risk zones, read from JSON config with built-in defaults as fallback"""
    raw = get_config_value(db, "dangerous_zones", "")
    if raw:
        try:
            return set(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            pass
    return set(DEFAULT_DANGEROUS_ZONES)


def get_session_timeout_minutes(db: Session) -> int:
    """Session timeout in minutes (default 30, clamped to 5–480)"""
    val = get_config_int(db, "session_timeout_minutes", 30)
    return max(5, min(val, 480))


def get_shadow_offline_days(db: Session) -> int:
    """Days threshold for long-term offline detection (default 30)"""
    return get_config_int(db, "shadow_offline_days", 30)


# ── V0.4 Cost Accounting ──────────────────────────────────────────────


def is_cost_accounting_enabled(db: Session) -> bool:
    """Whether the cost accounting feature is enabled (disabled by default)"""
    return get_config_value(db, "feature_cost_accounting_enabled", "false").lower() == "true"
