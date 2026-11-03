"""Quản lý phiên bản dataset: tạo version mới, undo, redo, khôi phục.

Nguyên tắc: phiên bản không bao giờ bị xóa hay sửa. Phiên bản "hiện tại" chỉ là con trỏ
datasets.current_version_id, nên undo/redo/restore chỉ đổi con trỏ. Mọi thao tác khóa dòng dataset
(SELECT ... FOR UPDATE) để hai người thao tác cùng lúc không tạo ra hai phiên bản trùng số.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.cleaning_operation import CleaningOperation
from app.models.dataset import Dataset, DatasetVersion
from app.repositories import dataset_repo
from app.schemas.rule import RuleSet
from app.services import storage
from app.services.audit import log_action
from app.services.frames import load_version_frame
from app.services.rules.engine import apply_rules
from app.services.rules.registry import RuleError

OP_LABELS = {
    "trim_whitespace": "Cắt khoảng trắng thừa",
    "change_case": "Đổi chữ hoa/thường",
    "replace_values": "Thay thế giá trị",
    "standardize_date": "Chuẩn hóa ngày",
    "standardize_phone": "Chuẩn hóa số điện thoại",
    "standardize_email": "Chuẩn hóa email",
    "cast_type": "Ép kiểu dữ liệu",
    "fill_missing": "Điền giá trị thiếu",
    "drop_duplicates": "Xóa dòng trùng lặp",
    "drop_rows_where": "Xóa dòng theo điều kiện",
    "flag_outliers": "Đánh dấu giá trị bất thường",
    "rename_column": "Đổi tên cột",
    "drop_column": "Xóa cột",
}


def summarize(rule_set: RuleSet) -> str:
    """Mô tả một lần áp dụng, ví dụ 'Áp dụng 2 bước: Cắt khoảng trắng thừa (ho_ten); ...'."""
    parts = [
        f"{OP_LABELS.get(s.op, s.op)} ({s.column})" if s.column else OP_LABELS.get(s.op, s.op)
        for s in rule_set.steps
    ]
    return f"Áp dụng {len(rule_set.steps)} bước: " + "; ".join(parts)


def _lock_dataset(db: Session, dataset_id: int) -> Dataset:
    dataset = db.get(Dataset, dataset_id, with_for_update=True)
    if dataset is None:
        raise NotFoundError("Không tìm thấy dataset.")
    return dataset


def _current_version(db: Session, dataset: Dataset) -> DatasetVersion:
    version = (
        db.get(DatasetVersion, dataset.current_version_id) if dataset.current_version_id else None
    )
    if version is None:
        raise ValidationAppError("Dataset chưa có phiên bản hiện tại.")
    return version


def _switch(
    db: Session,
    dataset: Dataset,
    version: DatasetVersion,
    user_id: int,
    action: str,
    old_version: DatasetVersion,
    ip_address: str | None,
) -> DatasetVersion:
    dataset.current_version_id = version.id
    log_action(
        db,
        user_id,
        action,
        "dataset",
        dataset.id,
        project_id=dataset.project_id,
        old_value={"version_number": old_version.version_number},
        new_value={"version_number": version.version_number},
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(version)
    return version


def create_new_version(
    db: Session,
    dataset_id: int,
    rule_set: RuleSet,
    user_id: int,
    ip_address: str | None = None,
) -> DatasetVersion:
    """Áp dụng rule_set lên phiên bản hiện tại, lưu kết quả thành phiên bản mới (là hiện tại).

    Ghi mỗi bước vào cleaning_operations (from -> to) và một dòng audit, cùng một giao dịch.
    Lỗi ở bất kỳ bước nào thì không có phiên bản hay file nào được tạo.
    """
    dataset = _lock_dataset(db, dataset_id)
    parent = _current_version(db, dataset)
    frame = load_version_frame(parent)
    try:
        result, step_results = apply_rules(frame, rule_set)
    except RuleError as exc:
        db.rollback()
        raise ValidationAppError(str(exc)) from exc
    if len(result) == 0:
        db.rollback()
        raise ValidationAppError("Kết quả không còn dòng dữ liệu nào nên không được áp dụng.")

    number = (
        db.scalar(
            select(func.max(DatasetVersion.version_number)).where(
                DatasetVersion.dataset_id == dataset.id
            )
        )
        or 0
    ) + 1
    key = storage.version_key(dataset.id, number)
    storage.save_dataframe_as_parquet(result, key)
    try:
        version = dataset_repo.create_version(
            db,
            dataset_id=dataset.id,
            version_number=number,
            storage_path=key,
            row_count=len(result),
            column_count=len(result.columns),
            created_by=user_id,
            parent_version_id=parent.id,
            change_summary=summarize(rule_set),
            commit=False,
        )
        for item in step_results:
            db.add(
                CleaningOperation(
                    from_version_id=parent.id,
                    to_version_id=version.id,
                    operation_type=item.step.op,
                    params={"column": item.step.column, **item.step.params},
                    rows_affected=item.affected_rows,
                    applied_by=user_id,
                )
            )
        log_action(
            db,
            user_id,
            "version.apply_rule",
            "dataset",
            dataset.id,
            project_id=dataset.project_id,
            old_value={"version_number": parent.version_number},
            new_value={"version_number": number, "change_summary": version.change_summary},
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_file(key)  # không để lại file mồ côi nếu ghi DB thất bại
        raise
    db.refresh(version)
    return version


def undo_version(
    db: Session, dataset_id: int, user_id: int, ip_address: str | None = None
) -> DatasetVersion:
    """Quay lại phiên bản cha của phiên bản hiện tại; không xóa phiên bản nào nên redo được."""
    dataset = _lock_dataset(db, dataset_id)
    current = _current_version(db, dataset)
    if current.parent_version_id is None:
        db.rollback()
        raise ValidationAppError("Không còn phiên bản trước để hoàn tác.")
    parent = db.get(DatasetVersion, current.parent_version_id)
    return _switch(db, dataset, parent, user_id, "version.undo", current, ip_address)


def redo_version(
    db: Session, dataset_id: int, user_id: int, ip_address: str | None = None
) -> DatasetVersion:
    """Tiến tới phiên bản con của phiên bản hiện tại có version_number lớn nhất."""
    dataset = _lock_dataset(db, dataset_id)
    current = _current_version(db, dataset)
    child = db.scalars(
        select(DatasetVersion)
        .where(DatasetVersion.parent_version_id == current.id)
        .order_by(DatasetVersion.version_number.desc())
        .limit(1)
    ).first()
    if child is None:
        db.rollback()
        raise ValidationAppError("Không có phiên bản nào để làm lại.")
    return _switch(db, dataset, child, user_id, "version.redo", current, ip_address)


def restore_version(
    db: Session, dataset_id: int, version_id: int, user_id: int, ip_address: str | None = None
) -> DatasetVersion:
    """Đặt một phiên bản bất kỳ của dataset làm phiên bản hiện tại."""
    dataset = _lock_dataset(db, dataset_id)
    current = _current_version(db, dataset)
    target = db.get(DatasetVersion, version_id)
    if target is None or target.dataset_id != dataset.id:
        db.rollback()
        raise NotFoundError("Không tìm thấy phiên bản này trong dataset.")
    return _switch(db, dataset, target, user_id, "version.restore", current, ip_address)
