"""API áp dụng rule, undo, redo, khôi phục phiên bản dataset."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user, get_db
from app.core.request_info import client_ip
from app.models.user import User
from app.schemas.dataset import DatasetVersionOut
from app.schemas.rule import RuleSet
from app.services import access, versioning

router = APIRouter(prefix="/versions", tags=["versions"])


@router.post("/{dataset_id}/apply", response_model=DatasetVersionOut)
async def apply_rule_set(
    dataset_id: int,
    rule_set: RuleSet,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Áp dụng rule_set lên version hiện tại, tạo version mới (chỉ sau khi user đã xem preview)."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    version = await run_in_threadpool(
        versioning.create_new_version, db, dataset.id, rule_set, current_user.id, client_ip(request)
    )
    return DatasetVersionOut.model_validate(version)


@router.post("/{dataset_id}/undo", response_model=DatasetVersionOut)
def undo(
    dataset_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Quay lại phiên bản trước."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    version = versioning.undo_version(db, dataset.id, current_user.id, client_ip(request))
    return DatasetVersionOut.model_validate(version)


@router.post("/{dataset_id}/redo", response_model=DatasetVersionOut)
def redo(
    dataset_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Tiến tới phiên bản kế tiếp (sau khi đã undo)."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    version = versioning.redo_version(db, dataset.id, current_user.id, client_ip(request))
    return DatasetVersionOut.model_validate(version)


@router.post("/{dataset_id}/restore/{version_id}", response_model=DatasetVersionOut)
def restore_version(
    dataset_id: int,
    version_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetVersionOut:
    """Khôi phục một phiên bản cụ thể trong lịch sử thành phiên bản hiện tại."""
    dataset = access.get_owned_dataset(db, current_user, dataset_id)
    version = versioning.restore_version(
        db, dataset.id, version_id, current_user.id, client_ip(request)
    )
    return DatasetVersionOut.model_validate(version)
