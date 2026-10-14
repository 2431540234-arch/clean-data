"""Test vòng đời dữ liệu trên schema đầy đủ: upload -> issue -> suggestion -> apply -> undo."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AIRequest,
    AuditLog,
    CleaningOperation,
    ColumnMapping,
    DataIssue,
    Dataset,
    DatasetVersion,
    Export,
    Job,
    Project,
    ProjectMember,
    QualityReport,
    Rule,
    SchemaProfile,
    Suggestion,
    User,
)
from app.models.rule import RULE_TYPES
from app.schemas.rule import ALLOWED_OPS
from app.services.audit import log_action

MIGRATION_0002 = Path(__file__).parents[2] / "alembic" / "versions" / "0002_complete_schema.py"


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _build_full_graph(db: Session, user: User) -> tuple[Project, Dataset, DatasetVersion]:
    """Tạo user -> project -> dataset -> v1 -> issue -> suggestion -> v2 -> operation -> report."""
    project = Project(name="Demo", description="Dự án thử", owner_id=user.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    db.add(ColumnMapping(project_id=project.id, source_name="SĐT", standard_name="so_dien_thoai"))

    dataset = Dataset(
        project_id=project.id,
        name="khach_hang",
        original_filename="khach_hang.csv",
        file_type="csv",
        file_size=1234,
        encoding="utf-8",
        uploaded_by=user.id,
    )
    db.add(dataset)
    db.flush()

    v1 = DatasetVersion(
        dataset_id=dataset.id,
        version_number=1,
        storage_path="datasets/1/v1.parquet",
        row_count=30,
        column_count=6,
        created_by=user.id,
    )
    db.add(v1)
    db.flush()
    dataset.current_version_id = v1.id

    db.add(
        SchemaProfile(
            version_id=v1.id,
            column_name="email",
            column_index=1,
            inferred_type="email",
            null_count=3,
            unique_count=25,
            null_ratio=0.1,
            unique_ratio=25 / 30,
            sample_values=["a@x.com"],
        )
    )
    issue = DataIssue(
        version_id=v1.id,
        row_index=4,
        column_name="email",
        issue_type="invalid_format",
        severity="medium",
        current_value=" TranThiBinh@GMAIL.com ",
        message="Email thừa khoảng trắng và viết hoa",
    )
    db.add(issue)
    db.flush()
    suggestion = Suggestion(
        version_id=v1.id,
        issue_id=issue.id,
        suggestion_type="fix",
        source="ai",
        target_column="email",
        proposed_rule={"steps": [{"op": "standardize_email", "column": "email"}]},
        explanation="Bỏ khoảng trắng và chuyển email về chữ thường.",
        confidence=0.9,
    )
    db.add(suggestion)
    db.flush()

    v2 = DatasetVersion(
        dataset_id=dataset.id,
        version_number=2,
        parent_version_id=v1.id,
        storage_path="datasets/1/v2.parquet",
        row_count=29,
        column_count=6,
        change_summary="Chuẩn hóa email",
        created_by=user.id,
    )
    db.add(v2)
    db.flush()
    db.add(
        CleaningOperation(
            from_version_id=v1.id,
            to_version_id=v2.id,
            suggestion_id=suggestion.id,
            operation_type="standardize_email",
            params={"column": "email"},
            rows_affected=3,
            applied_by=user.id,
        )
    )
    db.add(QualityReport(version_id=v2.id, overall_score=88.5, completeness=95, issue_summary={}))
    db.add(
        Export(version_id=v2.id, format="csv", storage_path="exports/1.csv", exported_by=user.id)
    )
    job = Job(job_type="apply_rules", dataset_id=dataset.id, version_id=v2.id, created_by=user.id)
    db.add(job)
    db.flush()
    db.add(
        AIRequest(
            user_id=user.id,
            job_id=job.id,
            provider="anthropic",
            model="m",
            purpose="x",
            status="success",
        )
    )
    dataset.current_version_id = v2.id
    db.commit()
    return project, dataset, v2


def test_full_lifecycle_and_undo(db: Session, normal_user: User) -> None:
    _, dataset, v2 = _build_full_graph(db, normal_user)

    assert dataset.current_version_id == v2.id
    assert v2.version_number == 2
    assert v2.quality_report.overall_score == 88.5
    assert dataset.current_version.parent_version.version_number == 1

    # undo = đổi current_version_id về parent_version_id
    dataset.current_version_id = v2.parent_version_id
    db.commit()
    db.refresh(dataset)
    assert dataset.current_version_id != v2.id
    assert dataset.current_version.version_number == 1

    profile = db.scalars(select(SchemaProfile)).one()
    assert profile.null_count == 3
    assert profile.null_ratio == pytest.approx(0.1)


def test_unique_and_check_constraints(db: Session, normal_user: User) -> None:
    project, dataset, v2 = _build_full_graph(db, normal_user)
    v1_id = v2.parent_version_id

    bad_objects = [
        DatasetVersion(dataset_id=dataset.id, version_number=1, storage_path="dup"),
        QualityReport(version_id=v2.id, overall_score=50),  # trùng version_id
        QualityReport(version_id=v1_id, overall_score=150),  # ngoài khoảng 0-100
        ProjectMember(project_id=project.id, user_id=normal_user.id, role="viewer"),  # trùng
        DataIssue(version_id=v2.id, issue_type="khong_ton_tai"),
        Rule(project_id=project.id, name="r", rule_type="khong_ton_tai"),
    ]
    for obj in bad_objects:
        db.add(obj)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_delete_project_cascades_but_keeps_audit_logs(db: Session, normal_user: User) -> None:
    project, dataset, _ = _build_full_graph(db, normal_user)
    log_action(
        db,
        user_id=normal_user.id,
        action="version.apply_rule",
        entity_type="dataset",
        entity_id=dataset.id,
        project_id=project.id,
        old_value={"version_number": 1},
        new_value={"version_number": 2, "op": "standardize_email"},
        ip_address="127.0.0.1",
    )
    db.add(
        Rule(project_id=None, name="rule hệ thống", rule_type="trim_whitespace", target_column="a")
    )
    db.commit()

    log = db.scalars(select(AuditLog)).one()
    assert (log.entity_type, log.entity_id, log.project_id) == ("dataset", dataset.id, project.id)
    assert log.old_value == {"version_number": 1}
    assert log.new_value == {"version_number": 2, "op": "standardize_email"}

    db.delete(project)
    db.commit()
    db.expire_all()

    for model in (
        Dataset,
        DatasetVersion,
        SchemaProfile,
        DataIssue,
        Suggestion,
        CleaningOperation,
        QualityReport,
        Export,
        Job,
        ProjectMember,
        ColumnMapping,
    ):
        assert _count(db, model) == 0, model.__name__

    assert _count(db, AuditLog) == 1  # audit log được giữ lại
    assert db.scalars(select(AuditLog)).one().project_id is None
    assert _count(db, AIRequest) == 1  # chỉ mất liên kết job, bản ghi vẫn còn
    assert db.scalars(select(AIRequest)).one().job_id is None
    assert _count(db, Rule) == 1  # rule hệ thống không thuộc project nên còn nguyên
    assert db.get(User, normal_user.id) is not None


def test_delete_user_sets_null_on_audit_and_cascades_projects(
    db: Session, normal_user: User, admin_user: User
) -> None:
    project, dataset, _ = _build_full_graph(db, normal_user)
    project_id = project.id  # đọc trước khi project bị xóa theo user
    log_action(
        db,
        user_id=normal_user.id,
        action="dataset.upload",
        entity_type="dataset",
        entity_id=dataset.id,
    )

    db.delete(normal_user)
    db.commit()
    db.expire_all()

    assert db.get(Project, project_id) is None
    log = db.scalars(select(AuditLog)).one()
    assert log.user_id is None
    assert db.get(User, admin_user.id) is not None


def test_rule_type_constraint_matches_dsl_and_migration() -> None:
    """CHECK của rules.rule_type gồm đúng các op của DSL + 'ruleset', ở cả model và migration."""
    assert set(RULE_TYPES) == ALLOWED_OPS | {"ruleset"}

    spec = importlib.util.spec_from_file_location("migration_0002", MIGRATION_0002)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert set(migration.RULE_TYPES) == set(RULE_TYPES)
