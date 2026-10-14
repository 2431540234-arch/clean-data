"""API quản lý rule template (lưu lại để tái sử dụng trong project)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.rule import RuleTemplateCreate, RuleTemplateOut

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/by-project/{project_id}", response_model=list[RuleTemplateOut])
def list_rule_templates(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RuleTemplateOut]:
    """Lấy toàn bộ rule template của một project."""
    raise NotImplementedError("TODO: lấy rule template theo project_id, kiểm tra quyền.")


@router.post("/by-project/{project_id}", response_model=RuleTemplateOut)
def create_rule_template(
    project_id: int,
    payload: RuleTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleTemplateOut:
    """Lưu một rule template mới cho project."""
    raise NotImplementedError("TODO: tạo Rule mới trong DB, kiểm tra quyền.")


@router.delete("/{rule_id}")
def delete_rule_template(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Xóa một rule template."""
    raise NotImplementedError("TODO: xóa Rule theo id, kiểm tra quyền qua project liên quan.")
