"""Hoàn thiện schema: bổ sung cột cho 9 bảng cũ và thêm 7 bảng mới.

Bảng mới: project_members, data_issues, cleaning_operations, column_mappings, jobs,
ai_requests, exports.

Thay đổi chính ở bảng cũ:
- Đổi tên cột (alter_column): datasets.created_by -> uploaded_by,
  dataset_versions.version_no -> version_number, suggestions.rule_json -> proposed_rule,
  quality_reports.score -> overall_score, quality_reports.metrics -> issue_summary.
- dataset_versions.is_current bị xóa, thay bằng datasets.current_version_id. Backfill từ bản ghi
  is_current (nếu một dataset có nhiều bản thì lấy version_number lớn nhất); downgrade dựng lại.
- schema_profiles: GIỮ null_ratio/unique_ratio, thêm null_count/unique_count
  (backfill = round(ratio * row_count)).
- suggestions: xóa severity (nay nằm ở data_issues.severity); source 'rule' -> 'rule_engine'.
- rules: rule_json được tách thành rule_type/target_column/params theo DSL RuleSet
  (một bước: rule_type = op; nhiều bước: rule_type = 'ruleset', params = toàn bộ RuleSet),
  rồi xóa rule_json; downgrade dựng lại rule_json.
- quality_reports: mỗi version một báo cáo; nếu trùng thì giữ bản mới nhất (có log cảnh báo).
- audit_logs: dataset_id/before_version/after_version/detail ->
  project_id/entity_type/entity_id/old_value/new_value (có backfill).
- Khai báo ondelete cho mọi khóa ngoại; các cột created_by/user_id chuyển sang nullable (SET NULL).
- project_members được backfill từ projects.owner_id (role 'owner').

Dữ liệu cũ được cập nhật TRƯỚC khi thêm CheckConstraint/unique. Trùng (dataset_id, version_number)
hoặc (version_id, column_name) làm migration dừng với thông báo rõ ràng, không tự xóa dữ liệu.

downgrade() khôi phục cấu trúc của 0001. Các cột bị đưa về NOT NULL (created_by, user_id)
sẽ làm downgrade thất bại nếu đã có dòng NULL (chủ ý, để không âm thầm gán sai dữ liệu).
Các cột chỉ có ở schema mới (ví dụ ip_address, confidence) bị mất dữ liệu khi downgrade.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
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
RULE_OPS_SQL = ", ".join(f"'{t}'" for t in RULE_OPS)

logger = logging.getLogger("alembic.runtime.migration")


def _now_col(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _replace_fk(table: str, column: str, ref: str, ondelete: str | None) -> None:
    """Xóa FK mặc định `<table>_<column>_fkey` rồi tạo lại với ondelete mới."""
    name = f"{table}_{column}_fkey"
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(
        name, table, ref.split(".")[0], [column], [ref.split(".")[1]], ondelete=ondelete
    )


def _fail_if_duplicates(sql: str, what: str) -> None:
    """Dừng migration nếu truy vấn `sql` (SELECT ... GROUP BY ... HAVING) trả về dòng nào."""
    rows = op.get_bind().execute(sa.text(sql)).fetchall()
    if rows:
        raise RuntimeError(
            f"Không thể thêm unique constraint: {what} bị trùng ở {len(rows)} nhóm, "
            f"ví dụ {tuple(rows[0])}. Hãy xử lý dữ liệu trùng rồi chạy lại migration."
        )


def upgrade() -> None:
    # ---------------- users ----------------
    op.add_column("users", _now_col("updated_at"))
    op.create_check_constraint("ck_users_role", "users", "role IN ('admin', 'user')")
    # 0001 tạo cả unique constraint lẫn index thường cho email; model dùng một unique index.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ---------------- projects ----------------
    op.add_column("projects", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("projects", _now_col("updated_at"))
    _replace_fk("projects", "owner_id", "users.id", "CASCADE")

    # ---------------- datasets (phần chưa phụ thuộc dataset_versions) ----------------
    op.drop_constraint("datasets_created_by_fkey", "datasets", type_="foreignkey")
    op.alter_column("datasets", "created_by", new_column_name="uploaded_by")
    op.alter_column("datasets", "uploaded_by", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "datasets_uploaded_by_fkey",
        "datasets",
        "users",
        ["uploaded_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_datasets_uploaded_by", "datasets", ["uploaded_by"])
    _replace_fk("datasets", "project_id", "projects.id", "CASCADE")
    op.add_column("datasets", sa.Column("file_type", sa.String(10), nullable=True))
    op.add_column("datasets", sa.Column("file_size", sa.BigInteger(), nullable=True))
    op.add_column("datasets", sa.Column("encoding", sa.String(50), nullable=True))
    op.add_column("datasets", sa.Column("sheet_name", sa.String(255), nullable=True))
    op.add_column("datasets", sa.Column("current_version_id", sa.Integer(), nullable=True))
    op.add_column("datasets", _now_col("updated_at"))
    op.create_check_constraint(
        "ck_datasets_file_type", "datasets", "file_type IN ('csv', 'xlsx', 'xls')"
    )

    # ---------------- dataset_versions ----------------
    op.alter_column("dataset_versions", "version_no", new_column_name="version_number")
    op.add_column(
        "dataset_versions",
        sa.Column("column_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("dataset_versions", sa.Column("change_summary", sa.Text(), nullable=True))
    _replace_fk("dataset_versions", "dataset_id", "datasets.id", "CASCADE")
    _replace_fk("dataset_versions", "parent_version_id", "dataset_versions.id", "SET NULL")
    op.alter_column("dataset_versions", "created_by", existing_type=sa.Integer(), nullable=True)
    _replace_fk("dataset_versions", "created_by", "users.id", "SET NULL")
    op.create_index(
        "ix_dataset_versions_parent_version_id", "dataset_versions", ["parent_version_id"]
    )
    op.create_index("ix_dataset_versions_created_by", "dataset_versions", ["created_by"])
    _fail_if_duplicates(
        "SELECT dataset_id, version_number FROM dataset_versions "
        "GROUP BY dataset_id, version_number HAVING COUNT(*) > 1",
        "(dataset_id, version_number) của dataset_versions",
    )
    op.create_unique_constraint(
        "uq_dataset_versions_dataset_id_version_number",
        "dataset_versions",
        ["dataset_id", "version_number"],
    )
    # datasets.current_version_id thay cho dataset_versions.is_current
    op.create_foreign_key(
        "datasets_current_version_id_fkey",
        "datasets",
        "dataset_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_datasets_current_version_id", "datasets", ["current_version_id"])
    op.execute(
        """
        UPDATE datasets d
        SET current_version_id = (
            SELECT v.id FROM dataset_versions v
            WHERE v.dataset_id = d.id AND v.is_current
            ORDER BY v.version_number DESC, v.id DESC
            LIMIT 1
        )
        """
    )
    op.drop_column("dataset_versions", "is_current")

    # ---------------- schema_profiles ----------------
    op.add_column("schema_profiles", sa.Column("column_index", sa.Integer(), nullable=True))
    op.add_column(
        "schema_profiles", sa.Column("null_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "schema_profiles",
        sa.Column("unique_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("schema_profiles", sa.Column("min_value", sa.Text(), nullable=True))
    op.add_column("schema_profiles", sa.Column("max_value", sa.Text(), nullable=True))
    op.add_column("schema_profiles", sa.Column("mean_value", sa.Float(), nullable=True))
    op.add_column("schema_profiles", sa.Column("detected_format", sa.String(100), nullable=True))
    op.execute(
        """
        UPDATE schema_profiles sp
        SET null_count = ROUND(sp.null_ratio * v.row_count)::int,
            unique_count = ROUND(sp.unique_ratio * v.row_count)::int
        FROM dataset_versions v
        WHERE v.id = sp.version_id
        """
    )
    _replace_fk("schema_profiles", "version_id", "dataset_versions.id", "CASCADE")
    _fail_if_duplicates(
        "SELECT version_id, column_name FROM schema_profiles "
        "GROUP BY version_id, column_name HAVING COUNT(*) > 1",
        "(version_id, column_name) của schema_profiles",
    )
    op.create_unique_constraint(
        "uq_schema_profiles_version_id_column", "schema_profiles", ["version_id", "column_name"]
    )

    # ---------------- data_issues (mới) ----------------
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
    op.alter_column("suggestions", "rule_json", new_column_name="proposed_rule")
    op.execute("UPDATE suggestions SET source = 'rule_engine' WHERE source = 'rule'")
    op.add_column("suggestions", sa.Column("issue_id", sa.Integer(), nullable=True))
    op.add_column(
        "suggestions",
        sa.Column("suggestion_type", sa.String(20), nullable=False, server_default="rule"),
    )
    op.add_column("suggestions", sa.Column("target_column", sa.String(255), nullable=True))
    op.add_column("suggestions", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("suggestions", sa.Column("reviewed_by", sa.Integer(), nullable=True))
    op.add_column(
        "suggestions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
    )
    _replace_fk("suggestions", "version_id", "dataset_versions.id", "CASCADE")
    op.create_foreign_key(
        "suggestions_issue_id_fkey",
        "suggestions",
        "data_issues",
        ["issue_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "suggestions_reviewed_by_fkey",
        "suggestions",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_suggestions_issue_id", "suggestions", ["issue_id"])
    op.create_index("ix_suggestions_reviewed_by", "suggestions", ["reviewed_by"])
    op.create_index("ix_suggestions_version_id_status", "suggestions", ["version_id", "status"])
    op.create_check_constraint(
        "ck_suggestions_suggestion_type",
        "suggestions",
        "suggestion_type IN ('fix', 'rule', 'column_mapping')",
    )
    op.create_check_constraint(
        "ck_suggestions_source", "suggestions", "source IN ('ai', 'rule_engine')"
    )
    op.create_check_constraint(
        "ck_suggestions_status", "suggestions", "status IN ('pending', 'accepted', 'rejected')"
    )
    op.create_check_constraint(
        "ck_suggestions_confidence",
        "suggestions",
        "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
    )
    # Mức độ nghiêm trọng nay nằm ở data_issues.severity (qua suggestions.issue_id).
    op.drop_column("suggestions", "severity")

    # ---------------- rules ----------------
    op.alter_column("rules", "project_id", existing_type=sa.Integer(), nullable=True)
    _replace_fk("rules", "project_id", "projects.id", "CASCADE")
    op.alter_column("rules", "created_by", existing_type=sa.Integer(), nullable=True)
    _replace_fk("rules", "created_by", "users.id", "SET NULL")
    op.create_index("ix_rules_created_by", "rules", ["created_by"])
    op.add_column(
        "rules", sa.Column("rule_type", sa.String(30), nullable=False, server_default="ruleset")
    )
    op.add_column("rules", sa.Column("target_column", sa.String(255), nullable=True))
    op.add_column(
        "rules",
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column("rules", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "rules", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column("rules", _now_col("updated_at"))
    # Rule một bước hợp lệ (đúng 1 khóa 'steps', 1 phần tử, op nằm trong DSL, params là object)
    # -> rule_type = op, target_column = column, params = params. Còn lại -> 'ruleset'.
    single_step = f"""
        jsonb_typeof(rule_json) = 'object'
        AND (SELECT COUNT(*) FROM jsonb_object_keys(rule_json)) = 1
        AND jsonb_typeof(rule_json -> 'steps') = 'array'
        AND jsonb_array_length(rule_json -> 'steps') = 1
        AND (rule_json -> 'steps' -> 0 ->> 'op') IN ({RULE_OPS_SQL})
        AND COALESCE(jsonb_typeof(rule_json -> 'steps' -> 0 -> 'params'), 'object') = 'object'
    """
    op.execute(
        f"""
        UPDATE rules SET
            rule_type = CASE WHEN {single_step} THEN rule_json -> 'steps' -> 0 ->> 'op'
                             ELSE 'ruleset' END,
            target_column = CASE WHEN {single_step} THEN rule_json -> 'steps' -> 0 ->> 'column'
                                 END,
            params = CASE WHEN {single_step}
                          THEN COALESCE(rule_json -> 'steps' -> 0 -> 'params', '{{}}'::jsonb)
                          ELSE rule_json END
        """
    )
    op.drop_column("rules", "rule_json")
    op.create_check_constraint("ck_rules_rule_type", "rules", f"rule_type IN ({RULE_TYPES_SQL})")

    # ---------------- cleaning_operations (mới) ----------------
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

    # ---------------- column_mappings (mới) ----------------
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

    # ---------------- quality_reports ----------------
    op.alter_column("quality_reports", "score", new_column_name="overall_score")
    op.alter_column("quality_reports", "metrics", new_column_name="issue_summary")
    for col in ("completeness", "uniqueness", "validity", "consistency"):
        op.add_column("quality_reports", sa.Column(col, sa.Float(), nullable=True))
    _replace_fk("quality_reports", "version_id", "dataset_versions.id", "CASCADE")
    # Mỗi version chỉ giữ báo cáo mới nhất trước khi thêm unique.
    deleted = op.get_bind().execute(
        sa.text(
            """
            DELETE FROM quality_reports q USING quality_reports n
            WHERE q.version_id = n.version_id
              AND (q.created_at < n.created_at OR (q.created_at = n.created_at AND q.id < n.id))
            """
        )
    )
    if deleted.rowcount:
        logger.warning(
            "quality_reports: đã xóa %s báo cáo cũ trùng version_id (giữ bản mới nhất).",
            deleted.rowcount,
        )
    op.execute(
        "UPDATE quality_reports SET overall_score = LEAST(100, GREATEST(0, overall_score)) "
        "WHERE overall_score < 0 OR overall_score > 100"
    )
    op.drop_index("ix_quality_reports_version_id", table_name="quality_reports")
    op.create_index("ix_quality_reports_version_id", "quality_reports", ["version_id"], unique=True)
    op.create_check_constraint(
        "ck_quality_overall", "quality_reports", "overall_score >= 0 AND overall_score <= 100"
    )
    for col in ("completeness", "uniqueness", "validity", "consistency"):
        op.create_check_constraint(
            f"ck_quality_{col}",
            "quality_reports",
            f"{col} IS NULL OR ({col} >= 0 AND {col} <= 100)",
        )

    # ---------------- jobs, ai_requests, exports (mới) ----------------
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

    # ---------------- project_members (mới) ----------------
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
    op.execute(
        "INSERT INTO project_members (project_id, user_id, role) "
        "SELECT id, owner_id, 'owner' FROM projects"
    )

    # ---------------- audit_logs ----------------
    op.add_column("audit_logs", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column(
        "audit_logs",
        sa.Column("entity_type", sa.String(50), nullable=False, server_default="system"),
    )
    op.add_column("audit_logs", sa.Column("entity_id", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("old_value", postgresql.JSONB(), nullable=True))
    op.add_column("audit_logs", sa.Column("new_value", postgresql.JSONB(), nullable=True))
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(45), nullable=True))
    op.execute(
        """
        UPDATE audit_logs a
        SET entity_type = CASE WHEN a.dataset_id IS NOT NULL THEN 'dataset' ELSE 'system' END,
            entity_id = a.dataset_id,
            project_id = (SELECT d.project_id FROM datasets d WHERE d.id = a.dataset_id),
            old_value = CASE WHEN a.before_version IS NOT NULL
                             THEN jsonb_build_object('version_number', a.before_version) END,
            new_value = CASE WHEN a.after_version IS NOT NULL OR a.detail <> '{}'::jsonb
                             THEN a.detail || CASE WHEN a.after_version IS NOT NULL
                                  THEN jsonb_build_object('version_number', a.after_version)
                                  ELSE '{}'::jsonb END END
        """
    )
    op.drop_index("ix_audit_logs_dataset_id", table_name="audit_logs")
    op.drop_column("audit_logs", "dataset_id")  # kéo theo FK tới datasets
    op.drop_column("audit_logs", "before_version")
    op.drop_column("audit_logs", "after_version")
    op.drop_column("audit_logs", "detail")
    op.alter_column("audit_logs", "user_id", existing_type=sa.Integer(), nullable=True)
    _replace_fk("audit_logs", "user_id", "users.id", "SET NULL")
    op.create_foreign_key(
        "audit_logs_project_id_fkey",
        "audit_logs",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"]
    )
    op.create_index(
        "ix_audit_logs_project_id_created_at", "audit_logs", ["project_id", "created_at"]
    )


def downgrade() -> None:
    # ---------------- audit_logs ----------------
    op.drop_index("ix_audit_logs_project_id_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type_entity_id", table_name="audit_logs")
    op.drop_constraint("audit_logs_project_id_fkey", "audit_logs", type_="foreignkey")
    op.add_column("audit_logs", sa.Column("dataset_id", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("before_version", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("after_version", sa.Integer(), nullable=True))
    op.add_column(
        "audit_logs",
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.execute(
        """
        UPDATE audit_logs
        SET dataset_id = CASE WHEN entity_type = 'dataset' THEN entity_id END,
            before_version = (old_value ->> 'version_number')::int,
            after_version = (new_value ->> 'version_number')::int,
            detail = COALESCE(new_value - 'version_number', '{}'::jsonb)
        """
    )
    # dataset_id có thể trỏ tới dataset đã bị xóa -> bỏ giá trị mồ côi trước khi tạo FK
    op.execute(
        "UPDATE audit_logs SET dataset_id = NULL "
        "WHERE dataset_id IS NOT NULL AND dataset_id NOT IN (SELECT id FROM datasets)"
    )
    op.create_foreign_key(
        "audit_logs_dataset_id_fkey", "audit_logs", "datasets", ["dataset_id"], ["id"]
    )
    op.create_index("ix_audit_logs_dataset_id", "audit_logs", ["dataset_id"])
    for col in ("ip_address", "new_value", "old_value", "entity_id", "entity_type", "project_id"):
        op.drop_column("audit_logs", col)
    _replace_fk("audit_logs", "user_id", "users.id", None)
    op.alter_column("audit_logs", "user_id", existing_type=sa.Integer(), nullable=False)

    # ---------------- bảng mới ----------------
    op.drop_table("project_members")
    op.drop_table("exports")
    op.drop_table("ai_requests")
    op.drop_table("jobs")

    # ---------------- quality_reports ----------------
    for col in ("completeness", "uniqueness", "validity", "consistency"):
        op.drop_constraint(f"ck_quality_{col}", "quality_reports", type_="check")
    op.drop_constraint("ck_quality_overall", "quality_reports", type_="check")
    op.drop_index("ix_quality_reports_version_id", table_name="quality_reports")
    op.create_index("ix_quality_reports_version_id", "quality_reports", ["version_id"])
    _replace_fk("quality_reports", "version_id", "dataset_versions.id", None)
    for col in ("consistency", "validity", "uniqueness", "completeness"):
        op.drop_column("quality_reports", col)
    op.alter_column("quality_reports", "issue_summary", new_column_name="metrics")
    op.alter_column("quality_reports", "overall_score", new_column_name="score")

    op.drop_table("column_mappings")
    op.drop_table("cleaning_operations")

    # ---------------- rules ----------------
    op.drop_constraint("ck_rules_rule_type", "rules", type_="check")
    op.add_column(
        "rules", sa.Column("rule_json", postgresql.JSONB(), nullable=False, server_default="{}")
    )
    op.execute(
        """
        UPDATE rules SET rule_json = CASE
            WHEN rule_type = 'ruleset' THEN params
            ELSE jsonb_build_object('steps', jsonb_build_array(jsonb_build_object(
                'op', rule_type, 'column', target_column, 'params', params)))
        END
        """
    )
    op.alter_column("rules", "rule_json", server_default=None)
    for col in ("updated_at", "is_active", "description", "params", "target_column", "rule_type"):
        op.drop_column("rules", col)
    op.drop_index("ix_rules_created_by", table_name="rules")
    _replace_fk("rules", "created_by", "users.id", None)
    op.alter_column("rules", "created_by", existing_type=sa.Integer(), nullable=False)
    _replace_fk("rules", "project_id", "projects.id", None)
    op.alter_column("rules", "project_id", existing_type=sa.Integer(), nullable=False)

    # ---------------- suggestions ----------------
    op.add_column(
        "suggestions",
        sa.Column("severity", sa.String(20), nullable=True, server_default="low"),
    )
    op.execute(
        "UPDATE suggestions s SET severity = i.severity "
        "FROM data_issues i WHERE i.id = s.issue_id"
    )
    for name in (
        "ck_suggestions_confidence",
        "ck_suggestions_status",
        "ck_suggestions_source",
        "ck_suggestions_suggestion_type",
    ):
        op.drop_constraint(name, "suggestions", type_="check")
    op.drop_index("ix_suggestions_version_id_status", table_name="suggestions")
    op.drop_index("ix_suggestions_reviewed_by", table_name="suggestions")
    op.drop_index("ix_suggestions_issue_id", table_name="suggestions")
    op.drop_constraint("suggestions_reviewed_by_fkey", "suggestions", type_="foreignkey")
    op.drop_constraint("suggestions_issue_id_fkey", "suggestions", type_="foreignkey")
    _replace_fk("suggestions", "version_id", "dataset_versions.id", None)
    for col in (
        "reviewed_at",
        "reviewed_by",
        "confidence",
        "target_column",
        "suggestion_type",
        "issue_id",
    ):
        op.drop_column("suggestions", col)
    op.execute("UPDATE suggestions SET source = 'rule' WHERE source = 'rule_engine'")
    op.alter_column("suggestions", "proposed_rule", new_column_name="rule_json")

    op.drop_table("data_issues")

    # ---------------- schema_profiles (null_ratio/unique_ratio vẫn còn nguyên) ----------------
    op.drop_constraint("uq_schema_profiles_version_id_column", "schema_profiles", type_="unique")
    _replace_fk("schema_profiles", "version_id", "dataset_versions.id", None)
    for col in (
        "detected_format",
        "mean_value",
        "max_value",
        "min_value",
        "unique_count",
        "null_count",
        "column_index",
    ):
        op.drop_column("schema_profiles", col)

    # ---------------- dataset_versions / datasets ----------------
    op.add_column(
        "dataset_versions",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE dataset_versions v
        SET is_current = TRUE
        FROM datasets d
        WHERE d.current_version_id = v.id
        """
    )
    op.drop_index("ix_datasets_current_version_id", table_name="datasets")
    op.drop_constraint("datasets_current_version_id_fkey", "datasets", type_="foreignkey")
    op.drop_constraint(
        "uq_dataset_versions_dataset_id_version_number", "dataset_versions", type_="unique"
    )
    op.drop_index("ix_dataset_versions_created_by", table_name="dataset_versions")
    op.drop_index("ix_dataset_versions_parent_version_id", table_name="dataset_versions")
    _replace_fk("dataset_versions", "created_by", "users.id", None)
    op.alter_column("dataset_versions", "created_by", existing_type=sa.Integer(), nullable=False)
    _replace_fk("dataset_versions", "parent_version_id", "dataset_versions.id", None)
    _replace_fk("dataset_versions", "dataset_id", "datasets.id", None)
    op.drop_column("dataset_versions", "change_summary")
    op.drop_column("dataset_versions", "column_count")
    op.alter_column("dataset_versions", "version_number", new_column_name="version_no")

    op.drop_constraint("ck_datasets_file_type", "datasets", type_="check")
    for col in (
        "updated_at",
        "current_version_id",
        "sheet_name",
        "encoding",
        "file_size",
        "file_type",
    ):
        op.drop_column("datasets", col)
    _replace_fk("datasets", "project_id", "projects.id", None)
    op.drop_index("ix_datasets_uploaded_by", table_name="datasets")
    op.drop_constraint("datasets_uploaded_by_fkey", "datasets", type_="foreignkey")
    op.alter_column("datasets", "uploaded_by", existing_type=sa.Integer(), nullable=False)
    op.alter_column("datasets", "uploaded_by", new_column_name="created_by")
    op.create_foreign_key("datasets_created_by_fkey", "datasets", "users", ["created_by"], ["id"])

    # ---------------- projects / users ----------------
    _replace_fk("projects", "owner_id", "users.id", None)
    op.drop_column("projects", "updated_at")
    op.drop_column("projects", "description")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"])
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "updated_at")
