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
    created_by: int
    created_at: datetime


class DatasetVersionOut(BaseModel):
    """Thông tin một phiên bản dataset trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    version_no: int
    row_count: int
    parent_version_id: int | None
    created_by: int
    created_at: datetime
    is_current: bool


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
