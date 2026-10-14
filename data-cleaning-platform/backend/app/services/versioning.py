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
       parent_version_id=parent_version.id, is_current=True (và set is_current=False
       cho version cũ).
    4. Ghi audit log qua app.services.audit.log_action.
    """
    raise NotImplementedError("TODO: áp dụng rule, lưu version mới, cập nhật is_current.")


def undo_version(db: Session, dataset_id: int, user_id: int) -> DatasetVersion:
    """Quay lại version cha của version hiện tại (is_current=True).

    Gợi ý cách làm: tìm current version, set is_current=False, set is_current=True
    cho parent_version_id tương ứng; nếu không có parent thì raise lỗi nghiệp vụ.
    """
    raise NotImplementedError("TODO: chuyển is_current về version cha.")


def redo_version(db: Session, dataset_id: int, user_id: int) -> DatasetVersion:
    """Tiến tới version con gần nhất (được tạo sau current, theo thời gian) của version hiện tại.

    Gợi ý cách làm: tìm version có parent_version_id = current.id, is_current=True cho nó.
    """
    raise NotImplementedError("TODO: chuyển is_current sang version con gần nhất.")
