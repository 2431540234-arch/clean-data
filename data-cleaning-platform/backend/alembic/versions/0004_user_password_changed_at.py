"""Thêm users.password_changed_at và chỉ mục audit_logs(action, created_at).

- password_changed_at: token cấp trước thời điểm này bị từ chối (sau khi đổi/đặt lại mật khẩu).
- ix_audit_logs_action_created_at: đếm nhanh các lần đăng nhập sai gần đây.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_audit_logs_action_created_at", "audit_logs", ["action", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action_created_at", table_name="audit_logs")
    op.drop_column("users", "password_changed_at")
