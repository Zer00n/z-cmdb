"""
Audit log service
All write operations must call this module to record logs
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    action_type: str,
    user: User | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    result: str = "success",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """
    Record an audit log entry.
    action_type: LOGIN / CREATE / UPDATE / DELETE / EXPORT / LLM_CALL / CONFIG
    """
    entry = AuditLog(
        timestamp=datetime.now(timezone.utc),
        user_id=user.id if user else None,
        username=user.username if user else None,
        user_role=user.role if user else None,
        action_type=action_type,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        ip_address=ip_address,
        user_agent=user_agent,
        details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
        result=result,
    )
    db.add(entry)
    db.flush()
    return entry


def log_from_request(
    db: Session,
    request: Request,
    action_type: str,
    user: User | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict | None = None,
    result: str = "success",
) -> AuditLog:
    """Extract IP and User-Agent from a FastAPI Request object"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]
    return log_action(
        db=db,
        action_type=action_type,
        user=user,
        target_type=target_type,
        target_id=target_id,
        details=details,
        result=result,
        ip_address=ip,
        user_agent=ua,
    )


def list_logs(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    action_type: str | None = None,
    user_id: int | None = None,
    target_type: str | None = None,
) -> tuple[list[AuditLog], int]:
    """Query audit logs (paginated)"""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    filters = []
    if action_type:
        filters.append(AuditLog.action_type == action_type)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if target_type:
        filters.append(AuditLog.target_type == target_type)

    if filters:
        from sqlalchemy import and_
        stmt = stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(AuditLog.timestamp.desc())
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    logs = list(db.scalars(stmt).all())
    return logs, total
