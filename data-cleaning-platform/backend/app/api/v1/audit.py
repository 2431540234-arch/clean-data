"""API audit log: user thường xem log của chính mình, admin xem toàn hệ thống."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_admin
from app.models.user import User
from app.repositories import audit_repo
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/me", response_model=list[AuditLogOut])
def get_my_audit_logs(
    limit: int = Query(audit_repo.DEFAULT_LIMIT, ge=1, le=audit_repo.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    """Audit log của chính user đang đăng nhập (mới nhất trước, mặc định 1000 dòng)."""
    return [
        AuditLogOut.model_validate(r)
        for r in audit_repo.list_for_user(db, current_user.id, limit, offset)
    ]


@router.get("/all", response_model=list[AuditLogOut], dependencies=[Depends(require_admin)])
def get_all_audit_logs(
    limit: int = Query(audit_repo.DEFAULT_LIMIT, ge=1, le=audit_repo.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    """Toàn bộ audit log hệ thống (chỉ admin; mới nhất trước, mặc định 1000 dòng)."""
    return [AuditLogOut.model_validate(r) for r in audit_repo.list_all(db, limit, offset)]
