"""API quản trị: quản lý user, khóa/mở, đổi quyền, thống kê hệ thống. Chỉ admin truy cập được."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.models.user import User
from app.schemas.admin import SystemStatsOut
from app.schemas.user import UserOut, UserUpdateByAdmin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Lấy danh sách toàn bộ user trong hệ thống."""
    raise NotImplementedError("TODO: dùng app.repositories.user_repo.list_all.")


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdateByAdmin, db: Session = Depends(get_db)) -> User:
    """Cập nhật role hoặc trạng thái khóa (is_active) của một user.

    Gợi ý cách làm: gọi app.services.user_admin.change_user_role và/hoặc
    app.services.user_admin.set_user_active tùy field nào được truyền trong payload.
    """
    raise NotImplementedError("TODO: cập nhật role/is_active qua app.services.user_admin.")


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Admin đặt lại mật khẩu cho một user (quên mật khẩu)."""
    raise NotImplementedError("TODO: dùng app.services.user_admin.reset_user_password.")


@router.get("/stats", response_model=SystemStatsOut)
def get_system_stats(db: Session = Depends(get_db)) -> SystemStatsOut:
    """Lấy thống kê tổng quan hệ thống (số user, dataset, lượt gọi AI, điểm TB)."""
    raise NotImplementedError("TODO: dùng app.services.system_stats.compute_system_stats.")
