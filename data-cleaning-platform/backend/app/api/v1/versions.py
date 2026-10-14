"""API áp dụng rule, undo, redo, khôi phục phiên bản dataset."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.dataset import DatasetVersionOut
from app.schemas.rule import RuleSet

router = APIRouter(prefix="/versions", tags=["versions"])


@router.post("/{dataset_id}/apply", response_model=DatasetVersionOut)
def apply_rule_set(
    dataset_id: int,
    rule_set: RuleSet,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Áp dụng rule_set lên version hiện tại, tạo version mới (chỉ sau khi user đã xem preview)."""
    raise NotImplementedError("TODO: dùng app.services.versioning.create_new_version.")


@router.post("/{dataset_id}/undo", response_model=DatasetVersionOut)
def undo(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Quay lại phiên bản trước."""
    raise NotImplementedError("TODO: dùng app.services.versioning.undo_version.")


@router.post("/{dataset_id}/redo", response_model=DatasetVersionOut)
def redo(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Tiến tới phiên bản kế tiếp (sau khi đã undo)."""
    raise NotImplementedError("TODO: dùng app.services.versioning.redo_version.")


@router.post("/{dataset_id}/restore/{version_id}", response_model=DatasetVersionOut)
def restore_version(
    dataset_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Khôi phục một phiên bản cụ thể trong lịch sử thành phiên bản hiện tại."""
    raise NotImplementedError(
        "TODO: set is_current=True cho version_id, False cho các version khác."
    )
