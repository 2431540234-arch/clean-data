"""Quản lý phiên bản dataset: tạo version mới, undo, redo."""

from sqlalchemy.orm import Session

from app.models.dataset import DatasetVersion
from app.schemas.rule import RuleSet


def create_new_version(
    db: Session, dataset_id: int, parent_version_id: int, rule_set: RuleSet, user_id: int
) -> DatasetVersion:
    """Áp dụng rule_set lên parent_version, lưu kết quả thành một version mới là current.

    Gợi ý cách làm:
    1. Đọc DataFrame của parent_version từ storage (app.services.storage).
    2. Chạy app.services.rules.engine.apply_rules.
    3. Lưu DataFrame kết quả lên storage, tạo DatasetVersion mới với
       parent_version_id=parent_version.id, version_number = số lớn nhất hiện có + 1,
       rồi gán datasets.current_version_id = id version mới; ghi cleaning_operations
       (from_version_id -> to_version_id).
    4. Ghi audit log qua app.services.audit.log_action.
    """
    raise NotImplementedError(
        "TODO: áp dụng rule, lưu version mới, cập nhật datasets.current_version_id."
    )


def undo_version(db: Session, dataset_id: int, user_id: int) -> DatasetVersion:
    """Quay lại version cha của version hiện tại (dataset.current_version_id).

    Gợi ý cách làm: đặt dataset.current_version_id = current_version.parent_version_id;
    nếu không có parent thì raise lỗi nghiệp vụ. Không xóa version nào để redo được.
    """
    raise NotImplementedError("TODO: đặt current_version_id về parent_version_id.")


def redo_version(db: Session, dataset_id: int, user_id: int) -> DatasetVersion:
    """Tiến tới version con gần nhất (version_number lớn nhất) của version hiện tại.

    Gợi ý cách làm: tìm version có parent_version_id = current_version_id, rồi đặt
    dataset.current_version_id = id của nó.
    """
    raise NotImplementedError("TODO: đặt current_version_id sang version con gần nhất.")
