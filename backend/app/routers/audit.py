"""
Audit log routes
GET  /api/audit/logs     Operation log list (super_admin + auditor)
POST /api/audit/export   Export audit report (auditor only)
"""
import csv
import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AnyUser, AuditorUser, get_current_user
from app.core.exceptions import PermissionDeniedError
from app.models.user import User
from app.schemas.audit import AuditLogListResponse
from app.services import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogListResponse)
def list_audit_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    action_type: str | None = None,
    user_id: int | None = None,
    target_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    """
    View operation logs.
    Permission: super_admin and auditor can view.
    """
    if current_user.role not in ("super_admin", "auditor"):
        raise PermissionDeniedError("Only super_admin and auditor can view operation logs")

    logs, total = audit_service.list_logs(
        db, page=page, page_size=page_size,
        action_type=action_type, user_id=user_id, target_type=target_type,
    )
    return AuditLogListResponse(
        items=logs,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/export")
def export_audit_report(
    current_user: AuditorUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """
    Export audit report (CSV).
    Permission: auditor only.
    """
    logs, _ = audit_service.list_logs(db, page=1, page_size=100000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Timestamp", "UserID", "Username", "Role",
        "ActionType", "TargetType", "TargetID", "SourceIP", "Result", "Details",
    ])
    for log in logs:
        writer.writerow([
            log.id, log.timestamp.isoformat(), log.user_id,
            log.username, log.user_role, log.action_type,
            log.target_type, log.target_id, log.ip_address,
            log.result, log.details or "",
        ])

    # Log the export operation itself
    audit_service.log_action(
        db, action_type="EXPORT", user=current_user,  # type: ignore[arg-type]
        target_type="audit_report", details={"count": len(logs)},
    )
    db.commit()

    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_report.csv"},
    )


@router.post("/export-pdf")
def export_audit_report_pdf(
    current_user: AuditorUser = None,
    db: Session = Depends(get_db),
) -> Response:
    """
    Export audit report (PDF).
    Permission: auditor only.
    """
    from fpdf import FPDF

    logs, _ = audit_service.list_logs(db, page=1, page_size=100000)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Z-CMDB Lite Audit Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Total records: {len(logs)}", ln=True, align="C")
    pdf.ln(5)

    # Table headers
    pdf.set_font("Helvetica", "B", 8)
    col_widths = [12, 30, 20, 18, 20, 20, 20, 25, 25]
    headers = ["ID", "Timestamp", "User", "Role", "Action", "Target", "TargetID", "IP", "Result"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 6, h, border=1)
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", "", 7)
    for log in logs[:500]:  # Limit to 500 rows to keep PDF size reasonable
        row = [
            str(log.id),
            log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "",
            log.username or "",
            log.user_role or "",
            log.action_type or "",
            log.target_type or "",
            str(log.target_id or ""),
            log.ip_address or "",
            log.result or "",
        ]
        for i, val in enumerate(row):
            pdf.cell(col_widths[i], 5, val[:15], border=1)
        pdf.ln()

    # Log the export operation
    audit_service.log_action(
        db, action_type="EXPORT", user=current_user,  # type: ignore[arg-type]
        target_type="audit_report", details={"format": "pdf", "count": len(logs)},
    )
    db.commit()

    pdf_bytes = pdf.output()
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=audit_report.pdf"},
    )


@router.get("/llm-logs")
def list_llm_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    LLM call log list.
    Permission: super_admin and auditor can view.
    """
    if current_user.role not in ("super_admin", "auditor"):
        raise PermissionDeniedError("Only super_admin and auditor can view LLM call logs")

    from sqlalchemy import func, select

    from app.models.llm_log import LlmCallLog

    count = db.scalar(select(func.count()).select_from(LlmCallLog)) or 0
    stmt = (
        select(LlmCallLog)
        .order_by(LlmCallLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = list(db.scalars(stmt).all())

    return {
        "items": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "user_id": log.user_id,
                "provider": log.provider,
                "model": log.model,
                "purpose": log.purpose,
                "elapsed_ms": log.elapsed_ms,
                "success": log.success,
                "sanitized_request": (log.sanitized_request or "")[:100],
                "response_summary": (log.response_summary or "")[:100],
            }
            for log in logs
        ],
        "total": count,
        "page": page,
        "page_size": page_size,
    }
