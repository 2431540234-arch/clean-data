"""API xuất dữ liệu đã làm sạch ra CSV/Excel kèm báo cáo chất lượng."""

import io
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user, get_db
from app.core.request_info import client_ip
from app.models.dataset import DatasetVersion
from app.models.export import Export
from app.models.user import User
from app.services import access, profiling_service, quality_service
from app.services.audit import log_action
from app.services.export import ensure_fits_excel, export_to_csv_bytes, export_to_excel_bytes
from app.services.frames import load_version_frame
from app.services.report import build_issues_dataframe, build_quality_report_dataframe

router = APIRouter(prefix="/export", tags=["export"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _download(content: bytes, filename: str, media_type: str) -> StreamingResponse:
    """Phản hồi tải file; tên file có dấu đi qua `filename*` (RFC 5987), kèm bản ASCII dự phòng."""
    ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "du_lieu"
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": disposition, "Content-Length": str(len(content))},
    )


def _file_name(dataset_name: str, version_number: int, extension: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", dataset_name, flags=re.UNICODE).strip("_") or "du_lieu"
    return f"{stem}_v{version_number}.{extension}"


def _record(
    db: Session,
    user: User,
    version: DatasetVersion,
    fmt: str,
    size: int,
    with_report: bool,
    ip: str | None,
) -> None:
    """Ghi lịch sử xuất file (chỉ metadata, không lưu bản sao file) và nhật ký."""
    db.add(
        Export(
            version_id=version.id,
            format=fmt,
            storage_path="",
            file_size=size,
            include_quality_report=with_report,
            exported_by=user.id,
        )
    )
    log_action(
        db,
        user.id,
        "dataset.export",
        "dataset",
        version.dataset_id,
        project_id=version.dataset.project_id,
        new_value={"format": fmt, "version_number": version.version_number, "bytes": size},
        ip_address=ip,
        commit=False,
    )
    db.commit()


def _build_csv(version: DatasetVersion) -> bytes:
    return export_to_csv_bytes(load_version_frame(version))


def _build_excel(db: Session, version: DatasetVersion) -> bytes:
    ensure_fits_excel("Dữ liệu", version.row_count)  # báo sớm, trước khi nạp cả bảng vào bộ nhớ
    report = quality_service.get_or_compute(db, version)
    issues = profiling_service.list_issues(db, version.id)
    return export_to_excel_bytes(
        {
            "Dữ liệu": load_version_frame(version),
            "Báo cáo chất lượng": build_quality_report_dataframe(report),
            "Lỗi đã phát hiện": build_issues_dataframe(issues),
        }
    )


@router.get("/{version_id}/csv")
async def export_csv(
    version_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Xuất dữ liệu của một phiên bản dataset ra file CSV (UTF-8-BOM)."""
    version = access.get_owned_version(db, current_user, version_id)
    content = await run_in_threadpool(_build_csv, version)
    _record(db, current_user, version, "csv", len(content), False, client_ip(request))
    name = _file_name(version.dataset.name, version.version_number, "csv")
    return _download(content, name, "text/csv; charset=utf-8")


@router.get("/{version_id}/excel")
async def export_excel(
    version_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Xuất dữ liệu kèm báo cáo chất lượng ra file Excel nhiều sheet."""
    version = access.get_owned_version(db, current_user, version_id)
    content = await run_in_threadpool(_build_excel, db, version)
    _record(db, current_user, version, "xlsx", len(content), True, client_ip(request))
    name = _file_name(version.dataset.name, version.version_number, "xlsx")
    return _download(content, name, XLSX_MIME)
