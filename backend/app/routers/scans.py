"""
Scan batch routes
POST   /api/scans/upload       Upload XML file
GET    /api/scans              Batch list
GET    /api/scans/{id}         Batch detail
POST   /api/scans/{id}/confirm Confirm import
DELETE /api/scans/{id}         Reject and delete batch
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.schemas.scan import (
    ScanBatchListResponse,
    ScanBatchRead,
    ScanConfirmRequest,
    ScanDiffResponse,
)
from app.services import scan_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("/upload", response_model=ScanBatchRead, status_code=201)
async def upload_scan(
    file: UploadFile = File(...),
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> ScanBatchRead:
    """Upload nmap XML file, parse it, and create a scan batch"""
    content = await file.read()
    batch = scan_service.upload_and_parse(
        db=db,
        file_content=content,
        filename=file.filename or "unknown.xml",
        user_id=current_user.id,  # type: ignore[union-attr]
    )
    return batch  # type: ignore[return-value]


@router.get("", response_model=ScanBatchListResponse)
def list_batches(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> ScanBatchListResponse:
    """Scan batch list"""
    skip = (page - 1) * page_size
    batches, total = scan_service.list_batches(db, skip=skip, limit=page_size)
    return ScanBatchListResponse(items=batches, total=total)  # type: ignore[arg-type]


@router.get("/{batch_id}", response_model=ScanBatchRead)
def get_batch(
    batch_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> ScanBatchRead:
    """Scan batch detail"""
    return scan_service.get_batch(db, batch_id)  # type: ignore[return-value]


@router.get("/{batch_id}/diff", response_model=ScanDiffResponse)
def get_batch_diff(
    batch_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> ScanDiffResponse:
    """Scan batch diff detail (lists of newly discovered / changed / disappeared hosts)"""
    return scan_service.get_batch_diff(db, batch_id)


@router.post("/{batch_id}/confirm", response_model=ScanBatchRead)
def confirm_batch(
    batch_id: int,
    body: ScanConfirmRequest,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> ScanBatchRead:
    """Confirm import batch"""
    return scan_service.confirm_batch(db, batch_id, body.new_assets or None)  # type: ignore[return-value]


@router.delete("/{batch_id}", status_code=204)
def reject_batch(
    batch_id: int,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> None:
    """Reject and delete batch"""
    scan_service.reject_batch(db, batch_id)
