"""API upload file, xem dữ liệu, chọn sheet Excel."""

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.dataset import DatasetOut, DatasetUploadResponse, DatasetVersionOut

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset(
    project_id: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    """Upload file CSV/Excel vào một project, tạo dataset + version đầu tiên.

    Gợi ý cách làm: kiểm tra quyền truy cập project (ensure_can_access_project), kiểm
    tra kích thước file <= settings.MAX_UPLOAD_MB, dùng app.services.ingestion.reader
    để đọc file, lưu DataFrame qua app.services.storage, tạo Dataset + DatasetVersion
    qua app.repositories.dataset_repo, ghi audit log "dataset.upload".
    """
    raise NotImplementedError("TODO: xử lý upload file, tạo dataset + version đầu tiên.")


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetOut:
    """Lấy thông tin một dataset (kiểm tra quyền qua project của nó)."""
    raise NotImplementedError("TODO: lấy dataset, kiểm tra quyền qua project liên quan.")


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersionOut])
def list_dataset_versions(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DatasetVersionOut]:
    """Lấy toàn bộ phiên bản của một dataset."""
    raise NotImplementedError("TODO: dùng app.repositories.dataset_repo để lấy versions.")


@router.post("/{dataset_id}/select-sheet", response_model=DatasetUploadResponse)
def select_sheet(
    dataset_id: int,
    sheet_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    """Chọn lại sheet khác của file Excel đã upload, tạo lại version đầu tiên từ sheet đó."""
    raise NotImplementedError("TODO: đọc lại sheet đã chọn và tạo version mới từ sheet đó.")
