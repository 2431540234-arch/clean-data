"""API CRUD project của chính user (admin xem được toàn bộ)."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.request_info import client_ip
from app.models.user import User
from app.repositories import dataset_repo, project_repo
from app.schemas.dataset import DatasetOut
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import access, storage
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectOut]:
    """Lấy danh sách project: admin thấy tất cả, user thường chỉ thấy project của mình."""
    projects = project_repo.list_for_user(db, current_user)
    counts = project_repo.dataset_counts(db, [p.id for p in projects])
    result = []
    for project in projects:
        out = ProjectOut.model_validate(project)
        out.dataset_count = counts.get(project.id, 0)
        result.append(out)
    return result


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Tạo project mới thuộc về user đang đăng nhập."""
    project = project_repo.create_project(db, payload.name, current_user.id, commit=False)
    log_action(
        db,
        current_user.id,
        "project.create",
        "project",
        project.id,
        project_id=project.id,
        new_value={"name": project.name},
        ip_address=client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Lấy thông tin một project (404 nếu không có, 403 nếu không phải owner/admin)."""
    return ProjectOut.model_validate(access.get_owned_project(db, current_user, project_id))


@router.get("/{project_id}/datasets", response_model=list[DatasetOut])
def list_project_datasets(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DatasetOut]:
    """Danh sách dataset của project (mới nhất trước) để chọn lại dataset sau khi tải lại trang."""
    project = access.get_owned_project(db, current_user, project_id)
    return [
        DatasetOut.model_validate(d) for d in dataset_repo.list_datasets_for_project(db, project.id)
    ]


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Cập nhật tên project."""
    project = access.get_owned_project(db, current_user, project_id)
    old_name = project.name
    project.name = payload.name
    log_action(
        db,
        current_user.id,
        "project.update",
        "project",
        project.id,
        project_id=project.id,
        old_value={"name": old_name},
        new_value={"name": project.name},
        ip_address=client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Xóa project cùng dataset, phiên bản, rule liên quan và file lưu trữ (owner hoặc admin)."""
    project = access.get_owned_project(db, current_user, project_id)
    name = project.name
    dataset_ids = project_repo.dataset_ids(db, project.id)
    # project_id của log để trống: dòng project sắp bị xóa nên khóa ngoại sẽ không còn hợp lệ.
    log_action(
        db,
        current_user.id,
        "project.delete",
        "project",
        project.id,
        old_value={"name": name, "dataset_count": len(dataset_ids)},
        ip_address=client_ip(request),
        commit=False,
    )
    project_repo.delete_project(db, project, commit=False)
    db.commit()
    # Dọn file sau khi DB đã commit; lỗi dọn file không làm hỏng thao tác (chỉ để lại file mồ côi).
    for dataset_id in dataset_ids:
        try:
            storage.delete_prefix(f"datasets/{dataset_id}")
        except storage.StorageError:
            logger.warning("Không dọn được file của dataset %s", dataset_id, exc_info=True)
    return {"message": f"Đã xóa dự án '{name}'."}
