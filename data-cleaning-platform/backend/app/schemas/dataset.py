"""Schema cho dataset và dataset version."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetOut(BaseModel):
    """Thông tin dataset trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    original_filename: str
    file_type: str | None
    file_size: int | None
    encoding: str | None
    sheet_name: str | None
    current_version_id: int | None
    uploaded_by: int | None
    created_at: datetime
    updated_at: datetime


class DatasetVersionOut(BaseModel):
    """Thông tin một phiên bản dataset (version hiện tại: DatasetOut.current_version_id)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    version_number: int
    row_count: int
    column_count: int
    parent_version_id: int | None
    change_summary: str | None
    created_by: int | None
    created_at: datetime


class DatasetPreviewRow(BaseModel):
    """Một dòng dữ liệu xem trước (preview) sau khi upload hoặc chọn sheet."""

    row_index: int
    values: dict[str, str | None]


class DatasetUploadResponse(BaseModel):
    """Phản hồi sau khi upload file thành công."""

    dataset: DatasetOut
    first_version: DatasetVersionOut
    sheet_names: list[str] = []
    preview_rows: list[DatasetPreviewRow] = []


class DatasetRowsPage(BaseModel):
    """Một trang dòng dữ liệu của một phiên bản (ô trống là null, row_index tính từ 0 cả bảng)."""

    version_id: int
    total: int
    offset: int
    limit: int
    columns: list[str]
    rows: list[DatasetPreviewRow]


class UploadStartIn(BaseModel):
    """Mở phiên tải lên theo từng phần: tên file, tổng dung lượng (byte) và SHA-256 (tùy chọn)."""

    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)
    sha256: str | None = Field(default=None, description="SHA-256 của cả file (hex 64 ký tự)")


class UploadSessionOut(BaseModel):
    """Phiên tải lên đã mở: mã phiên và kích thước tối đa mỗi phần client được gửi."""

    upload_id: str
    part_size_bytes: int
    max_bytes: int
    expires_in_minutes: int


class UploadPartOut(BaseModel):
    """Kết quả nhận một phần: số thứ tự và tổng byte server đã nhận của phiên."""

    index: int
    received_bytes: int


class UploadCompleteIn(BaseModel):
    """Kết thúc phiên: tổng số phần đã gửi (đánh số 0..parts-1)."""

    parts: int = Field(ge=1)
