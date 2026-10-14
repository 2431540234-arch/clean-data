"""API audit log: user thường xem log của chính mình, admin xem toàn hệ thống."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/me", response_model=list[AuditLogOut])
def get_my_audit_logs(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[AuditLogOut]:
    """Lấy audit log của chính user đang đăng nhập."""
    raise NotImplementedError("TODO: dùng app.repositories.audit_repo.list_for_user.")


@router.get("/all", response_model=list[AuditLogOut], dependencies=[Depends(require_admin)])
def get_all_audit_logs(db: Session = Depends(get_db)) -> list[AuditLogOut]:
    """Lấy toàn bộ audit log hệ thống (chỉ admin)."""
    raise NotImplementedError("TODO: dùng app.repositories.audit_repo.list_all.")
