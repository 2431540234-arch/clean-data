"""Nghiệp vụ tạo dataset từ file tải lên: kiểm tra, đọc, lưu file gốc + phiên bản 1, ghi nhật ký."""

import logging
import re
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationAppError
from app.models.dataset import Dataset, DatasetVersion
from app.models.project import Project
from app.models.user import User
from app.repositories import dataset_repo
from app.schemas.dataset import DatasetPreviewRow
from app.services import storage
from app.services.audit import log_action
from app.services.ingestion.reader import (
    ReadResult,
    file_type_from_name,
    list_excel_sheets,
    read_dataset_file,
    read_excel_sheet,
)

logger = logging.getLogger(__name__)

PREVIEW_ROWS = 20
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


@dataclass
class UploadOutcome:
    """Kết quả tạo/đọc lại dataset để router dựng DatasetUploadResponse."""

    dataset: Dataset
    version: DatasetVersion
    sheet_names: list[str]
    frame: pd.DataFrame


def sanitize_filename(filename: str | None) -> str:
    """Chỉ giữ tên file (bỏ đường dẫn), bỏ ký tự điều khiển, giới hạn độ dài."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = _CONTROL_CHARS.sub("", name).strip()
    if len(name) > 255:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: 250 - len(ext)] + dot + ext) if dot else name[:255]
    if not name:
        raise ValidationAppError("Tên file không hợp lệ.")
    return name


def preview_rows(frame: pd.DataFrame, limit: int = PREVIEW_ROWS) -> list[DatasetPreviewRow]:
    """Các dòng đầu của bảng; ô trống -> None (đúng hợp đồng DatasetPreviewRow)."""
    rows = []
    for index, record in enumerate(frame.head(limit).to_dict("records")):
        values = {str(col): (None if val == "" else str(val)) for col, val in record.items()}
        rows.append(DatasetPreviewRow(row_index=index, values=values))
    return rows


def create_dataset_from_file(
    db: Session,
    user: User,
    project: Project,
    filename: str | None,
    content: bytes,
    ip_address: str | None = None,
) -> UploadOutcome:
    """Đọc file và tạo dataset + phiên bản 1; lỗi giữa chừng thì hoàn tác cả DB lẫn file."""
    safe_name = sanitize_filename(filename)
    file_type = file_type_from_name(safe_name)
    result: ReadResult = read_dataset_file(content, safe_name)
    frame = result.dataframe

    dataset = None
    try:
        dataset = dataset_repo.create_dataset(
            db,
            project_id=project.id,
            name=safe_name.rsplit(".", 1)[0][:255],
            original_filename=safe_name,
            uploaded_by=user.id,
            file_type=file_type,
            file_size=len(content),
            encoding=result.encoding,
            sheet_name=result.used_sheet,
            commit=False,
        )
        storage.save_bytes(storage.original_key(dataset.id, file_type), content)
        key = storage.version_key(dataset.id, 1)
        storage.save_dataframe_as_parquet(frame, key)
        version = dataset_repo.create_version(
            db,
            dataset_id=dataset.id,
            version_number=1,
            storage_path=key,
            row_count=len(frame),
            column_count=len(frame.columns),
            created_by=user.id,
            change_summary="Tải lên ban đầu",
            commit=False,
        )
        log_action(
            db,
            user.id,
            "dataset.upload",
            "dataset",
            dataset.id,
            project_id=project.id,
            new_value={"filename": safe_name, "rows": len(frame), "columns": len(frame.columns)},
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        if dataset is not None and dataset.id is not None:
            _cleanup(dataset.id)
        raise
    db.refresh(dataset)
    db.refresh(version)
    return UploadOutcome(dataset, version, result.sheet_names, frame)


def _cleanup(dataset_id: int) -> None:
    try:
        storage.delete_prefix(f"datasets/{dataset_id}")
    except Exception:  # noqa: BLE001 - dọn dẹp không được che mất lỗi gốc đang xử lý
        logger.warning("Không dọn được file của dataset %s", dataset_id, exc_info=True)


def reselect_sheet(
    db: Session,
    user: User,
    dataset: Dataset,
    sheet_name: str,
    ip_address: str | None = None,
) -> UploadOutcome:
    """Đọc lại sheet khác của file Excel gốc và thay nội dung phiên bản 1.

    Chỉ cho phép khi dataset chưa có phiên bản làm sạch nào (nếu không sẽ phá lịch sử), và xóa
    các kết quả phân tích gắn với phiên bản 1 cũ (profiling, vấn đề, gợi ý, báo cáo chất lượng).
    """
    if dataset.file_type not in ("xlsx", "xls"):
        raise ValidationAppError("Dataset này không phải file Excel.")
    versions = dataset_repo.list_versions(db, dataset.id)
    if len(versions) != 1:
        raise ConflictError(
            "Dataset đã có phiên bản làm sạch nên không thể đổi sheet. Hãy tải file lên lại."
        )
    version = versions[0]
    try:
        content = storage.load_bytes(storage.original_key(dataset.id, dataset.file_type))
    except storage.StorageError as exc:
        raise ValidationAppError("Không tìm thấy file gốc để đọc lại sheet.") from exc
    sheets = list_excel_sheets(content)
    if sheet_name not in sheets:
        raise ValidationAppError("Sheet không tồn tại trong file.")
    frame = read_excel_sheet(content, sheet_name)

    old_sheet = dataset.sheet_name
    storage.save_dataframe_as_parquet(frame, version.storage_path)
    version.row_count = len(frame)
    version.column_count = len(frame.columns)
    dataset.sheet_name = sheet_name
    for collection in (
        version.schema_profiles,
        version.data_issues,
        version.suggestions,
        version.exports,
    ):
        for item in list(collection):
            db.delete(item)
    if version.quality_report is not None:
        db.delete(version.quality_report)
    log_action(
        db,
        user.id,
        "dataset.select_sheet",
        "dataset",
        dataset.id,
        project_id=dataset.project_id,
        old_value={"sheet_name": old_sheet},
        new_value={"sheet_name": sheet_name, "rows": len(frame)},
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(dataset)
    db.refresh(version)
    return UploadOutcome(dataset, version, sheets, frame)
