"""Khởi tạo toàn bộ schema: 16 bảng nghiệp vụ.

Nhóm bảng:
- Người dùng: users, project_members
- Dữ liệu: projects, datasets, dataset_versions, schema_profiles, column_mappings
- Lỗi và gợi ý: data_issues, suggestions, rules, cleaning_operations
- Chất lượng, xuất file: quality_reports, exports
- Tác vụ nền, AI, nhật ký: jobs, ai_requests, audit_logs

Phiên bản đang dùng của dataset được xác định bởi datasets.current_version_id (khóa ngoại tới
dataset_versions, tạo sau khi cả hai bảng đã có để tránh vòng phụ thuộc). Mọi khóa ngoại đều khai
báo ondelete; các cột created_by/user_id cho phép NULL (SET NULL khi xóa user).

Migration này đã gộp migration 0002 cũ (bổ sung cột cho 9 bảng đầu và thêm 7 bảng mới) vào 0001.
Database đã tạo từ chuỗi 0001 + 0002 cũ có cấu trúc giống hệt; chỉ cần chạy
`alembic stamp --purge 0001` (hoặc đổi alembic_version.version_num về '0001') để Alembic nhận ra.

Revision ID: 0001
Revises:
Create Date: 2026-01-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Bản sao của app.schemas.rule.ALLOWED_OPS tại thời điểm migration (migration không import code
# app để không đổi nghĩa khi DSL thay đổi) + 'ruleset' cho rule nhiều bước.
RULE_OPS = (
    "cast_type",
    "change_case",
    "drop_column",
    "drop_duplicates",
    "drop_rows_where",
    "fill_missing",
    "flag_outliers",
    "rename_column",
    "replace_values",
    "standardize_date",
    "standardize_email",
    "standardize_phone",
    "trim_whitespace",
)
RULE_TYPES = (*RULE_OPS, "ruleset")
RULE_TYPES_SQL = ", ".join(f"'{t}'" for t in RULE_TYPES)


def _now_col(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    # ---------------- users ----------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _now_col("created_at"),
        _now_col("updated_at"),
        sa.CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ---------------- projects ----------------
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        _now_col("created_at"),
        sa.Column("description", sa.Text(), nullable=True),
        _now_col("updated_at"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    # ---------------- project_members ----------------
    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        _now_col("created_at"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_id_user_id"),
        sa.CheckConstraint("role IN ('owner', 'editor', 'viewer')", name="ck_project_members_role"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])

    # ---------------- datasets ----------------
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _now_col("created_at"),
        sa.Column("file_type", sa.String(10), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("encoding", sa.String(50), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        _now_col("updated_at"),
        sa.CheckConstraint("file_type IN ('csv', 'xlsx', 'xls')", name="ck_datasets_file_type"),
    )
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"])
    op.create_index("ix_datasets_uploaded_by", "datasets", ["uploaded_by"])

    # ---------------- dataset_versions ----------------
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "parent_version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _now_col("created_at"),
        sa.Column("column_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "dataset_id", "version_number", name="uq_dataset_versions_dataset_id_version_number"
        ),
    )
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"])
    op.create_index(
        "ix_dataset_versions_parent_version_id", "dataset_versions", ["parent_version_id"]
    )
    op.create_index("ix_dataset_versions_created_by", "dataset_versions", ["created_by"])

    # datasets.current_version_id trỏ tới dataset_versions (vòng phụ thuộc -> tạo FK sau)
    op.create_foreign_key(
        "datasets_current_version_id_fkey",
        "datasets",
        "dataset_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_datasets_current_version_id", "datasets", ["current_version_id"])

    # ---------------- schema_profiles ----------------
    op.create_table(
        "schema_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("column_name", sa.String(255), nullable=False),
        sa.Column("inferred_type", sa.String(50), nullable=False),
        sa.Column("null_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unique_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sample_values", postgresql.JSONB(), nullable=False, server_default="[]"),
        _now_col("created_at"),
        sa.Column("column_index", sa.Integer(), nullable=True),
        sa.Column("null_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_value", sa.Text(), nullable=True),
        sa.Column("max_value", sa.Text(), nullable=True),
        sa.Column("mean_value", sa.Float(), nullable=True),
        sa.Column("detected_format", sa.String(100), nullable=True),
        sa.UniqueConstraint(
            "version_id", "column_name", name="uq_schema_profiles_version_id_column"
        ),
    )
    op.create_index("ix_schema_profiles_version_id", "schema_profiles", ["version_id"])

    # ---------------- column_mappings ----------------
    op.create_table(
        "column_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("standard_name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(50), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        _now_col("created_at"),
        sa.UniqueConstraint("project_id", "source_name", name="uq_column_mappings_project_source"),
    )
    op.create_index("ix_column_mappings_project_id", "column_mappings", ["project_id"])

    # ---------------- data_issues ----------------
    op.create_table(
        "data_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=True),
        sa.Column("column_name", sa.String(255), nullable=True),
        sa.Column("issue_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="low"),
        sa.Column("current_value", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        _now_col("created_at"),
        sa.CheckConstraint(
            "issue_type IN ('duplicate', 'missing', 'outlier', 'invalid_format', "
            "'type_mismatch', 'inconsistent')",
            name="ck_data_issues_issue_type",
        ),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_data_issues_severity"),
        sa.CheckConstraint("status IN ('open', 'fixed', 'ignored')", name="ck_data_issues_status"),
    )
    op.create_index("ix_data_issues_version_id", "data_issues", ["version_id"])
    op.create_index(
        "ix_data_issues_version_id_issue_type", "data_issues", ["version_id", "issue_type"]
    )
    op.create_index(
        "ix_data_issues_version_id_column_name", "data_issues", ["version_id", "column_name"]
    )

    # ---------------- suggestions ----------------
    op.create_table(
        "suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("proposed_rule", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        _now_col("created_at"),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("data_issues.id", ondelete="SET NULL")),
        sa.Column("suggestion_type", sa.String(20), nullable=False, server_default="rule"),
        sa.Column("target_column", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "suggestion_type IN ('fix', 'rule', 'column_mapping')",
            name="ck_suggestions_suggestion_type",
        ),
        sa.CheckConstraint("source IN ('ai', 'rule_engine')", name="ck_suggestions_source"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')", name="ck_suggestions_status"
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_suggestions_confidence",
        ),
    )
    op.create_index("ix_suggestions_version_id", "suggestions", ["version_id"])
    op.create_index("ix_suggestions_issue_id", "suggestions", ["issue_id"])
    op.create_index("ix_suggestions_reviewed_by", "suggestions", ["reviewed_by"])
    op.create_index("ix_suggestions_version_id_status", "suggestions", ["version_id", "status"])

    # ---------------- rules ----------------
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _now_col("created_at"),
        sa.Column("rule_type", sa.String(30), nullable=False, server_default="ruleset"),
        sa.Column("target_column", sa.String(255), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _now_col("updated_at"),
        sa.CheckConstraint(f"rule_type IN ({RULE_TYPES_SQL})", name="ck_rules_rule_type"),
    )
    op.create_index("ix_rules_project_id", "rules", ["project_id"])
    op.create_index("ix_rules_created_by", "rules", ["created_by"])

    # ---------------- cleaning_operations ----------------
    op.create_table(
        "cleaning_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "from_version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("rules.id", ondelete="SET NULL")),
        sa.Column(
            "suggestion_id", sa.Integer(), sa.ForeignKey("suggestions.id", ondelete="SET NULL")
        ),
        sa.Column("operation_type", sa.String(100), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rows_affected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applied_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    for col in ("from_version_id", "to_version_id", "rule_id", "suggestion_id", "applied_by"):
        op.create_index(f"ix_cleaning_operations_{col}", "cleaning_operations", [col])

    # ---------------- quality_reports ----------------
    op.create_table(
        "quality_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("issue_summary", postgresql.JSONB(), nullable=False, server_default="{}"),
        _now_col("created_at"),
        sa.Column("completeness", sa.Float(), nullable=True),
        sa.Column("uniqueness", sa.Float(), nullable=True),
        sa.Column("validity", sa.Float(), nullable=True),
        sa.Column("consistency", sa.Float(), nullable=True),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100", name="ck_quality_overall"
        ),
        *[
            sa.CheckConstraint(
                f"{col} IS NULL OR ({col} >= 0 AND {col} <= 100)", name=f"ck_quality_{col}"
            )
            for col in ("completeness", "uniqueness", "validity", "consistency")
        ],
    )
    # Mỗi version một báo cáo
    op.create_index("ix_quality_reports_version_id", "quality_reports", ["version_id"], unique=True)

    # ---------------- jobs ----------------
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_type", sa.String(30), nullable=False),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("datasets.id", ondelete="CASCADE")),
        sa.Column(
            "version_id", sa.Integer(), sa.ForeignKey("dataset_versions.id", ondelete="CASCADE")
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _now_col("created_at"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "job_type IN ('profile', 'detect_issues', 'ai_suggest', 'apply_rules', 'export')",
            name="ck_jobs_job_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'done', 'failed')", name="ck_jobs_status"
        ),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress"),
    )
    for col in ("dataset_id", "version_id", "status", "created_by"):
        op.create_index(f"ix_jobs_{col}", "jobs", [col])

    # ---------------- ai_requests ----------------
    op.create_table(
        "ai_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        _now_col("created_at"),
        sa.CheckConstraint("provider IN ('openai', 'anthropic')", name="ck_ai_requests_provider"),
        sa.CheckConstraint("status IN ('success', 'error')", name="ck_ai_requests_status"),
    )
    op.create_index("ix_ai_requests_user_id", "ai_requests", ["user_id"])
    op.create_index("ix_ai_requests_job_id", "ai_requests", ["job_id"])

    # ---------------- exports ----------------
    op.create_table(
        "exports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Integer(),
            sa.ForeignKey("dataset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("include_quality_report", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("exported_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _now_col("created_at"),
        sa.CheckConstraint("format IN ('csv', 'xlsx', 'parquet')", name="ck_exports_format"),
    )
    op.create_index("ix_exports_version_id", "exports", ["version_id"])
    op.create_index("ix_exports_exported_by", "exports", ["exported_by"])

    # ---------------- audit_logs ----------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        _now_col("created_at"),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("entity_type", sa.String(50), nullable=False, server_default="system"),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("old_value", postgresql.JSONB(), nullable=True),
        sa.Column("new_value", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index(
        "ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"]
    )
    op.create_index(
        "ix_audit_logs_project_id_created_at", "audit_logs", ["project_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("exports")
    op.drop_table("ai_requests")
    op.drop_table("jobs")
    op.drop_table("quality_reports")
    op.drop_table("cleaning_operations")
    op.drop_table("rules")
    op.drop_table("suggestions")
    op.drop_table("data_issues")
    op.drop_table("column_mappings")
    op.drop_table("schema_profiles")
    # Gỡ FK vòng datasets -> dataset_versions trước khi xóa hai bảng
    op.drop_constraint("datasets_current_version_id_fkey", "datasets", type_="foreignkey")
    op.drop_table("dataset_versions")
    op.drop_table("datasets")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("users")
