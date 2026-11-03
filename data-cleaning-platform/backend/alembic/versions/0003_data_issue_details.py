"""Thêm affected_count và details cho data_issues.

Một dòng data_issues mô tả cả nhóm lỗi của một cột (vd. "12 ngày sai định dạng"), nên cần số dòng
bị ảnh hưởng và chi tiết (loại lỗi cụ thể, giá trị mẫu, bảng sửa) để hiển thị và sinh gợi ý.

Revision ID: 0003
Revises: 0001
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "data_issues",
        sa.Column("affected_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "data_issues",
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("data_issues", "details")
    op.drop_column("data_issues", "affected_count")
