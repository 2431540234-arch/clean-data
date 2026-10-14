"""API CRUD project của chính user (admin xem được toàn bộ)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectOut]:
    """Lấy danh sách project: admin thấy tất cả, user thường chỉ thấy project của mình."""
    raise NotImplementedError("TODO: dùng app.repositories.project_repo.list_for_user.")


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Tạo project mới thuộc về user đang đăng nhập."""
    raise NotImplementedError("TODO: dùng app.repositories.project_repo.create_project.")


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Lấy thông tin một project. Dùng ensure_can_access_project để chặn truy cập chéo."""
    raise NotImplementedError(
        "TODO: lấy project, gọi ensure_can_access_project(current_user, project)."
    )


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Cập nhật tên project."""
    raise NotImplementedError(
        "TODO: kiểm tra quyền bằng ensure_can_access_project rồi cập nhật tên project."
    )


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Xóa project (chỉ owner hoặc admin)."""
    raise NotImplementedError(
        "TODO: kiểm tra quyền bằng ensure_can_access_project rồi xóa project."
    )
