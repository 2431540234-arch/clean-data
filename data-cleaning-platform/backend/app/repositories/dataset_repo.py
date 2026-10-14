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
    """Lấy version hiện tại (is_current=True) của một dataset."""
    raise NotImplementedError("TODO: select DatasetVersion where dataset_id và is_current=True.")


def get_version_by_id(db: Session, version_id: int) -> DatasetVersion | None:
    """Lấy một version cụ thể theo id."""
    return db.get(DatasetVersion, version_id)


def create_dataset(
    db: Session, project_id: int, name: str, original_filename: str, created_by: int
) -> Dataset:
    """Tạo dataset mới thuộc project_id."""
    raise NotImplementedError("TODO: tạo Dataset mới, add/commit/refresh.")


def create_version(
    db: Session,
    dataset_id: int,
    version_no: int,
    storage_path: str,
    row_count: int,
    created_by: int,
    parent_version_id: int | None = None,
    is_current: bool = True,
) -> DatasetVersion:
    """Tạo một DatasetVersion mới. Nếu is_current=True, phải set is_current=False cho version cũ."""
    raise NotImplementedError(
        "TODO: tạo DatasetVersion mới, cập nhật cờ is_current cho version cũ."
    )
