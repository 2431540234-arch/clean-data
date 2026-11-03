"""Truy vấn DB cho bảng datasets và dataset_versions."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetVersion


def get_dataset_by_id(db: Session, dataset_id: int) -> Dataset | None:
    """Lấy dataset theo id."""
    return db.get(Dataset, dataset_id)


def list_datasets_for_project(db: Session, project_id: int) -> list[Dataset]:
    """Lấy toàn bộ dataset thuộc một project (mới nhất trước)."""
    stmt = (
        select(Dataset)
        .where(Dataset.project_id == project_id)
        .order_by(Dataset.created_at.desc(), Dataset.id.desc())
    )
    return list(db.scalars(stmt))


def get_current_version(db: Session, dataset_id: int) -> DatasetVersion | None:
    """Lấy version hiện tại của một dataset (version mà datasets.current_version_id trỏ tới)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.current_version_id is None:
        return None
    return db.get(DatasetVersion, dataset.current_version_id)


def get_version_by_id(db: Session, version_id: int) -> DatasetVersion | None:
    """Lấy một version cụ thể theo id."""
    return db.get(DatasetVersion, version_id)


def list_versions(db: Session, dataset_id: int) -> list[DatasetVersion]:
    """Toàn bộ phiên bản của dataset, theo thứ tự version_number tăng dần."""
    stmt = (
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_number)
    )
    return list(db.scalars(stmt))


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
    commit: bool = True,
) -> Dataset:
    """Tạo dataset mới thuộc project_id (commit=False: chỉ flush để lấy id)."""
    dataset = Dataset(
        project_id=project_id,
        name=name,
        original_filename=original_filename,
        uploaded_by=uploaded_by,
        file_type=file_type,
        file_size=file_size,
        encoding=encoding,
        sheet_name=sheet_name,
    )
    db.add(dataset)
    if commit:
        db.commit()
        db.refresh(dataset)
    else:
        db.flush()
    return dataset


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
    commit: bool = True,
) -> DatasetVersion:
    """Tạo DatasetVersion mới; nếu make_current thì đặt datasets.current_version_id = id mới."""
    version = DatasetVersion(
        dataset_id=dataset_id,
        version_number=version_number,
        storage_path=storage_path,
        row_count=row_count,
        column_count=column_count,
        created_by=created_by,
        parent_version_id=parent_version_id,
        change_summary=change_summary,
    )
    db.add(version)
    db.flush()
    if make_current:
        dataset = db.get(Dataset, dataset_id)
        dataset.current_version_id = version.id
    if commit:
        db.commit()
        db.refresh(version)
    else:
        db.flush()
    return version
