"""API quản lý rule template (lưu lại để tái sử dụng trong project)."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.core.request_info import client_ip
from app.models.rule import Rule
from app.models.user import User
from app.schemas.rule import RuleTemplateCreate, RuleTemplateOut, rule_set_to_columns
from app.services import access
from app.services.audit import log_action
from app.services.rules.engine import MAX_STEPS

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/by-project/{project_id}", response_model=list[RuleTemplateOut])
def list_rule_templates(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RuleTemplateOut]:
    """Lấy toàn bộ rule template của một project (mới nhất trước)."""
    project = access.get_owned_project(db, current_user, project_id)
    stmt = select(Rule).where(Rule.project_id == project.id).order_by(Rule.id.desc())
    return [RuleTemplateOut.model_validate(rule) for rule in db.scalars(stmt)]


@router.post("/by-project/{project_id}", response_model=RuleTemplateOut)
def create_rule_template(
    project_id: int,
    payload: RuleTemplateCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleTemplateOut:
    """Lưu một rule template mới cho project."""
    project = access.get_owned_project(db, current_user, project_id)
    name = payload.name.strip()
    if not name:
        raise ValidationAppError("Tên rule không được để trống.")
    if not payload.rule_set.steps:
        raise ValidationAppError("Rule phải có ít nhất một bước.")
    if len(payload.rule_set.steps) > MAX_STEPS:
        raise ValidationAppError(f"Một rule tối đa {MAX_STEPS} bước.")
    rule = Rule(
        project_id=project.id,
        name=name,
        description=payload.description,
        created_by=current_user.id,
        **rule_set_to_columns(payload.rule_set),
    )
    db.add(rule)
    db.flush()
    log_action(
        db,
        current_user.id,
        "rule.create",
        "project",
        project.id,
        project_id=project.id,
        new_value={"rule_id": rule.id, "name": name},
        ip_address=client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(rule)
    return RuleTemplateOut.model_validate(rule)


@router.delete("/{rule_id}")
def delete_rule_template(
    rule_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Xóa một rule template (owner project hoặc admin; rule hệ thống chỉ admin)."""
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise NotFoundError("Không tìm thấy rule.")
    if rule.project_id is None:
        if current_user.role != "admin":
            raise ForbiddenError("Chỉ quản trị viên mới được xóa rule hệ thống.")
    else:
        access.get_owned_project(db, current_user, rule.project_id)
    name = rule.name
    log_action(
        db,
        current_user.id,
        "rule.delete",
        "project" if rule.project_id else "system",
        rule.project_id,
        project_id=rule.project_id,
        old_value={"rule_id": rule.id, "name": name},
        ip_address=client_ip(request),
        commit=False,
    )
    db.delete(rule)
    db.commit()
    return {"message": f"Đã xóa rule '{name}'."}
