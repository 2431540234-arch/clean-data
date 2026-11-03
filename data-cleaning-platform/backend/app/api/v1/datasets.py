"""API upload file, xem dữ liệu, chọn sheet Excel."""

from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError, PayloadTooLargeError, ValidationAppError
from app.core.request_info import client_ip
from app.models.user import User
from app.repositories import dataset_repo
from app.schemas.dataset import (
    DatasetOut,
    DatasetPreviewRow,
    DatasetRowsPage,
    DatasetUploadResponse,
    DatasetVersionOut,
)
from app.services import access, dataset_service
from app.services.frames import load_version_rows

router = APIRouter(prefix="/datasets", tags=["datasets"])

_CHUNK = 1024 * 1024


async def _read_limited(file: UploadFile) -> bytes:
    """Đọc từng khối và dừng ngay khi vượt giới hạn, không nạp cả file khổng lồ vào RAM."""
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise PayloadTooLargeError(f"File vượt quá {settings.MAX_UPLOAD_MB} MB.")
        chunks.append(chunk)
    return b"".join(chunks)


def _response(outcome: dataset_service.UploadOutcome) -> DatasetUploadResponse:
    return DatasetUploadResponse(
        dataset=DatasetOut.model_validate(outcome.dataset),
        first_version=DatasetVersionOut.model_validate(outcome.version),
        sheet_names=outcome.sheet_names,
        preview_rows=dataset_service.preview_rows(outcome.frame),
    )


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset(
    project_id: int,
    file: UploadFile,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    """Upload file CSV/Excel vào một project, tạo dataset + version đầu tiên."""
    project = access.get_owned_project(db, current_user, project_id)
    if not file.filename:
        raise ValidationAppError("Chưa chọn file.")
    content = await _read_limited(file)
    outcome = await run_in_threadpool(
        dataset_service.create_dataset_from_file,
        db,
        current_user,
        project,
        file.filename,
        content,
        client_ip(request),
    )
    return _response(outcome)


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetOut:
    """Lấy thông tin một dataset (kiểm tra quyền qua project của nó)."""
    return DatasetOut.model_validate(access.get_owned_dataset(db, current_user, dataset_id))


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionOut])
def list_dataset_versions(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DatasetVersionOut]:
    """Lấy toàn bộ phiên bản của một dataset (theo version_number tăng dần)."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    return [DatasetVersionOut.model_validate(v) for v in dataset_repo.list_versions(db, dataset.id)]


@router.get("/{dataset_id}/versions/{version_id}/rows", response_model=DatasetRowsPage)
def list_version_rows(
    dataset_id: int,
    version_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetRowsPage:
    """Xem các dòng dữ liệu của một phiên bản theo trang (offset/limit, tối đa 1000 dòng/trang)."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    version = dataset_repo.get_version_by_id(db, version_id)
    if version is None or version.dataset_id != dataset.id:
        raise NotFoundError("Không tìm thấy phiên bản này trong dataset.")
    columns, total, rows = load_version_rows(version, offset, limit)
    return DatasetRowsPage(
        version_id=version.id,
        total=total,
        offset=offset,
        limit=limit,
        columns=columns,
        rows=[
            DatasetPreviewRow(row_index=offset + i, values=values) for i, values in enumerate(rows)
        ],
    )


@router.post("/{dataset_id}/select-sheet", response_model=DatasetUploadResponse)
def select_sheet(
    dataset_id: int,
    sheet_name: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    """Chọn lại sheet khác của file Excel đã upload, tạo lại version đầu tiên từ sheet đó."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    outcome = dataset_service.reselect_sheet(
        db, current_user, dataset, sheet_name, client_ip(request)
    )
    return _response(outcome)
