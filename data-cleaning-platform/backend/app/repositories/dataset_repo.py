"""Truy vấn DB cho bảng datasets và dataset_versions."""

from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetVersion


def get_dataset_by_id(db: Session, dataset_id: int) -> Dataset | None:
    """Lấy dataset theo id."""
    return db.get(Dataset, dataset_id)


def list_datasets_for_project(db: Session, project_id: int) -> list[Dataset]:
    """Lấy toàn bộ dataset thuộc một project."""
    raise NotImplementedError("TODO: select Dataset where project_id = project_id.")


def get_current_version(db: Session, dataset_id: int) -> DatasetVersion | None:
    """Lấy version hiện tại của một dataset (version mà datasets.current_version_id trỏ tới)."""
    raise NotImplementedError(
        "TODO: lấy Dataset rồi trả dataset.current_version (None nếu current_version_id NULL)."
    )


def get_version_by_id(db: Session, version_id: int) -> DatasetVersion | None:
    """Lấy một version cụ thể theo id."""
    return db.get(DatasetVersion, version_id)


def create_dataset(
    db: Session,
    project_id: int,
    name: str,
    original_filename: str,
    uploaded_by: int,
    file_type: str | None = None,
    file_size: int | None = None,
    encoding: str | None = None,
    sheet_name: str | None = None,
) -> Dataset:
    """Tạo dataset mới thuộc project_id."""
    raise NotImplementedError("TODO: tạo Dataset mới, add/commit/refresh.")


def create_version(
    db: Session,
    dataset_id: int,
    version_number: int,
    storage_path: str,
    row_count: int,
    column_count: int,
    created_by: int,
    parent_version_id: int | None = None,
    change_summary: str | None = None,
    make_current: bool = True,
) -> DatasetVersion:
    """Tạo DatasetVersion mới; nếu make_current thì đặt datasets.current_version_id = id mới."""
    raise NotImplementedError(
        "TODO: tạo DatasetVersion mới; nếu make_current thì gán dataset.current_version_id."
    )
