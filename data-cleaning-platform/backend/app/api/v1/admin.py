"""API quản trị: quản lý user, khóa/mở, đổi quyền, thống kê hệ thống. Chỉ admin truy cập được."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.core.exceptions import ValidationAppError
from app.core.request_info import client_ip
from app.models.user import User
from app.repositories import user_repo
from app.schemas.admin import SystemStatsOut
from app.schemas.user import UserOut, UserUpdateByAdmin
from app.services import user_admin
from app.services.system_stats import compute_system_stats

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[User]:
    """Lấy danh sách toàn bộ user trong hệ thống."""
    return user_repo.list_all(db)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateByAdmin,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    """Cập nhật role và/hoặc trạng thái khóa (is_active) của một user (chỉ gửi trường cần đổi)."""
    if payload.role is None and payload.is_active is None:
        raise ValidationAppError("Không có thông tin nào để cập nhật.")
    ip = client_ip(request)
    # Hai thay đổi (nếu có) nằm trong CÙNG một giao dịch: hoặc cả hai thành công, hoặc không gì cả.
    try:
        user = None
        if payload.role is not None:
            user = user_admin.change_user_role(
                db, admin.id, user_id, payload.role, ip, commit=False
            )
        if payload.is_active is not None:
            user = user_admin.set_user_active(
                db, admin.id, user_id, payload.is_active, ip, commit=False
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    """Admin đặt lại mật khẩu cho một user: trả mật khẩu tạm để báo cho user (hiện một lần)."""
    new_password = user_admin.reset_user_password(db, admin.id, user_id, client_ip(request))
    return {
        "new_password": new_password,
        "message": "Đã đặt lại mật khẩu. Hãy gửi mật khẩu tạm này cho người dùng và nhắc đổi lại.",
    }


@router.get("/stats", response_model=SystemStatsOut)
def get_system_stats(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> SystemStatsOut:
    """Lấy thống kê tổng quan hệ thống (số user, dataset, lượt gọi AI, điểm TB)."""
    return compute_system_stats(db)
