"""Schema cho dataset và dataset version."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
