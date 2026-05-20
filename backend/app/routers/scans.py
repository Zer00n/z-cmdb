"""
扫描批次路由
POST   /api/scans/upload       上传 XML 文件
GET    /api/scans              批次列表
GET    /api/scans/{id}         批次详情
POST   /api/scans/{id}/confirm 确认导入
DELETE /api/scans/{id}         拒绝并删除批次
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
    """上传 nmap XML 文件，解析并创建扫描批次"""
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
    """扫描批次列表"""
    skip = (page - 1) * page_size
    batches, total = scan_service.list_batches(db, skip=skip, limit=page_size)
    return ScanBatchListResponse(items=batches, total=total)  # type: ignore[arg-type]


@router.get("/{batch_id}", response_model=ScanBatchRead)
def get_batch(
    batch_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> ScanBatchRead:
    """扫描批次详情"""
    return scan_service.get_batch(db, batch_id)  # type: ignore[return-value]


@router.get("/{batch_id}/diff", response_model=ScanDiffResponse)
def get_batch_diff(
    batch_id: int,
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> ScanDiffResponse:
    """扫描批次差异详情（新发现/变更/消失主机列表）"""
    return scan_service.get_batch_diff(db, batch_id)


@router.post("/{batch_id}/confirm", response_model=ScanBatchRead)
def confirm_batch(
    batch_id: int,
    body: ScanConfirmRequest,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> ScanBatchRead:
    """确认导入批次"""
    return scan_service.confirm_batch(db, batch_id, body.new_assets or None)  # type: ignore[return-value]


@router.delete("/{batch_id}", status_code=204)
def reject_batch(
    batch_id: int,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> None:
    """拒绝并删除批次"""
    scan_service.reject_batch(db, batch_id)
