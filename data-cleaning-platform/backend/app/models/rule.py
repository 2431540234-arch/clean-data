"""Model Rule: rule đã lưu để tái sử dụng (theo project hoặc rule hệ thống)."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.rule import ALLOWED_OPS

if TYPE_CHECKING:
    from app.models.project import Project

# rule_type = tên op của DSL (app.schemas.rule.ALLOWED_OPS) cho rule một bước, hoặc 'ruleset'
# cho rule nhiều bước (params chứa nguyên RuleSet). Migration 0002 giữ bản sao danh sách này;
# test_rule_type_constraint_matches_dsl bắt lỗi nếu hai bên lệch nhau.
RULE_TYPES = (*sorted(ALLOWED_OPS), "ruleset")
_RULE_TYPES_SQL = ", ".join(f"'{t}'" for t in RULE_TYPES)


class Rule(Base):
    """Rule template do user lưu lại; project_id = NULL nghĩa là rule hệ thống.

    Rule một bước: rule_type = op, target_column = column, params = params của bước đó.
    Rule nhiều bước: rule_type = 'ruleset', params = toàn bộ RuleSet ({"steps": [...]}).
    Chuyển đổi qua app.schemas.rule.rule_set_to_columns / columns_to_rule_set.
    """

    __tablename__ = "rules"
    __table_args__ = (
        CheckConstraint(f"rule_type IN ({_RULE_TYPES_SQL})", name="ck_rules_rule_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ruleset")
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped["Project | None"] = relationship(back_populates="rules")
