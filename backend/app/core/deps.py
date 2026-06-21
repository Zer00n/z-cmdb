"""
FastAPI 依赖注入
get_current_user + 角色检查依赖项
"""
import logging
from typing import Annotated

from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.models.user import User
from app.repositories import user_repo

logger = logging.getLogger(__name__)


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    """
    从 Authorization: Bearer <token> 解析当前用户。
    失败时抛 AuthenticationError（全局 handler 转 401）。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("缺少认证 Token")

    token = authorization[len("Bearer "):]
    payload = decode_token(token, expected_type="access")

    user_id = int(payload["sub"])
    user = user_repo.get_by_id(db, user_id)

    if user.status == "disabled":
        raise AuthenticationError("账号已被禁用")

    return user


# ── 角色检查依赖项 ────────────────────────────────────────────


def require_super_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """仅 super_admin 可访问"""
    if current_user.role != "super_admin":
        raise PermissionDeniedError("需要超级管理员权限")
    return current_user


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """super_admin 和 admin 可访问"""
    if current_user.role not in ("super_admin", "admin"):
        raise PermissionDeniedError("需要管理员权限")
    return current_user


def require_auditor(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """auditor 专属（审计员角色）"""
    if current_user.role != "auditor":
        raise PermissionDeniedError("需要审计员权限")
    return current_user


def require_any(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """任何已登录用户均可访问"""
    return current_user


# ── 类型别名，方便路由使用 ────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
AdminUser = Annotated[User, Depends(require_admin)]
AuditorUser = Annotated[User, Depends(require_auditor)]
AnyUser = Annotated[User, Depends(require_any)]


def require_auditor_exists(
    db: Session = Depends(get_db),
) -> None:
    """
    PRD 3.3：必须创建至少一个 auditor 角色账号才能解锁完整功能。
    在关键操作（扫描上传、拓扑生成、报表导出）前检查。
    """
    from app.services.config_service import has_auditor_user
    if not has_auditor_user(db):
        raise PermissionDeniedError(
            "系统尚未创建审计员账号。请先在用户管理中创建至少一个 auditor 角色用户，才能使用完整功能。"
        )


AuditorExists = Annotated[None, Depends(require_auditor_exists)]


# ── V0.4 成本核算功能开关依赖 ───────────────────────────────────


def _require_cost_feature(
    db: Session = Depends(get_db),
) -> None:
    """集中校验成本核算功能开关，关闭时抛 FeatureDisabledError。
    所有成本/账单/费率/关系路由统一挂此依赖，禁止各接口内重复判断。"""
    from app.services.config_service import is_cost_accounting_enabled
    from app.core.exceptions import FeatureDisabledError
    if not is_cost_accounting_enabled(db):
        raise FeatureDisabledError("资产成本核算功能未启用，请在系统配置中开启")


RequireCostFeature = Annotated[None, Depends(_require_cost_feature)]
