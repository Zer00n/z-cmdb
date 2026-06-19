"""
系统配置读取服务
从 system_configs 表读取运行时可调配置项
"""
import json

from sqlalchemy.orm import Session

from app.models.config import SystemConfig


def get_config_value(db: Session, key: str, default: str = "") -> str:
    """从 system_configs 表读取配置值，不存在则返回默认值"""
    cfg = db.get(SystemConfig, key)
    if cfg is None or cfg.value is None:
        return default
    return cfg.value


def get_config_int(db: Session, key: str, default: int = 0) -> int:
    """读取整数配置"""
    val = get_config_value(db, key, str(default))
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_missing_threshold(db: Session) -> int:
    """消失保护阈值（默认 3）"""
    return get_config_int(db, "missing_threshold", 3)


def get_upload_max_size_mb(db: Session) -> int:
    """上传文件大小上限 MB（默认 50）"""
    return get_config_int(db, "upload_max_size_mb", 50)


def get_asset_no_prefix(db: Session) -> str:
    """资产编号前缀（默认 CMDB）"""
    return get_config_value(db, "asset_no_prefix", "CMDB")


def has_auditor_user(db: Session) -> bool:
    """检查系统中是否存在至少一个 active 的 auditor 用户"""
    from sqlalchemy import select, func
    from app.models.user import User
    count = db.scalar(
        select(func.count()).select_from(User).where(
            User.role == "auditor", User.status == "active"
        )
    ) or 0
    return count > 0


# ── 大屏配置 ──────────────────────────────────────────────────

DEFAULT_DANGEROUS_PORTS = [21, 22, 23, 135, 139, 445, 1433, 1521, 2375,
                           3306, 3389, 5432, 5984, 6379, 8080, 8888, 9200, 11211, 27017]
DEFAULT_DANGEROUS_ZONES = ["dmz", "office"]


def get_dashboard_refresh_seconds(db: Session) -> int:
    """大屏自动刷新间隔（默认 30 秒）"""
    return get_config_int(db, "dashboard_refresh_seconds", 30)


def get_dashboard_list_limit(db: Session) -> int:
    """大屏各滚动列表返回上限（默认 50）"""
    return get_config_int(db, "dashboard_list_limit", 50)


def get_dangerous_ports_list(db: Session) -> set[int]:
    """危险端口清单，从 JSON 配置读取，回退内置默认"""
    raw = get_config_value(db, "dangerous_ports_list", "")
    if raw:
        try:
            return set(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            pass
    return set(DEFAULT_DANGEROUS_PORTS)


def get_dangerous_zones(db: Session) -> set[str]:
    """高危区域，从 JSON 配置读取，回退内置默认"""
    raw = get_config_value(db, "dangerous_zones", "")
    if raw:
        try:
            return set(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            pass
    return set(DEFAULT_DANGEROUS_ZONES)


def get_shadow_offline_days(db: Session) -> int:
    """长期离线判定天数（默认 30）"""
    return get_config_int(db, "shadow_offline_days", 30)
