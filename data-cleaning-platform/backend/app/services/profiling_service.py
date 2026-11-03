"""Chạy và lưu profiling + phát hiện lỗi cho một phiên bản dataset."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.data_issue import DataIssue
from app.models.dataset import DatasetVersion
from app.models.schema_profile import SchemaProfile
from app.schemas.issue import DataIssueOut
from app.services.detectors import run_all_detectors
from app.services.detectors.base import DetectionIssue
from app.services.frames import load_version_frame
from app.services.profiling.profiler import profile_dataframe

STORED_ROW_INDICES = (
    100  # chỉ lưu vài dòng đầu bị ảnh hưởng để xem nhanh, không lưu hàng triệu chỉ số
)
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def get_profiles(db: Session, version_id: int) -> list[SchemaProfile]:
    """Thống kê cột đã lưu của phiên bản, theo thứ tự cột."""
    stmt = (
        select(SchemaProfile)
        .where(SchemaProfile.version_id == version_id)
        .order_by(SchemaProfile.column_index)
    )
    return list(db.scalars(stmt))


def get_profiles_or_404(db: Session, version_id: int) -> list[SchemaProfile]:
    profiles = get_profiles(db, version_id)
    if not profiles:
        raise NotFoundError("Chưa chạy profiling cho phiên bản này.")
    return profiles


def run_profiling(db: Session, version: DatasetVersion) -> list[SchemaProfile]:
    """Chạy profiling + detector và lưu kết quả; đã chạy rồi thì trả lại kết quả cũ.

    Phiên bản dữ liệu bất biến nên kết quả không thay đổi: chạy lại là không cần thiết, và giữ
    nguyên các dòng lỗi giúp những gợi ý đã gắn với chúng không bị mất liên kết.
    """
    # Khóa dòng phiên bản để hai request chạy cùng lúc không ghi trùng kết quả.
    db.get(DatasetVersion, version.id, with_for_update=True)
    existing = get_profiles(db, version.id)
    if existing:
        db.rollback()
        return existing

    frame = load_version_frame(version)
    columns = profile_dataframe(frame)
    types = {c.column_name: c.inferred_type for c in columns}
    detected = run_all_detectors(frame, types)

    for column in columns:
        db.add(
            SchemaProfile(
                version_id=version.id,
                column_name=column.column_name,
                column_index=column.column_index,
                inferred_type=column.inferred_type,
                null_count=column.null_count,
                unique_count=column.unique_count,
                null_ratio=column.null_ratio,
                unique_ratio=column.unique_ratio,
                min_value=column.min_value,
                max_value=column.max_value,
                mean_value=column.mean_value,
                sample_values=column.sample_values,
                detected_format=column.detected_format,
            )
        )
    for issue in detected:
        db.add(_to_row(version.id, issue))
    db.commit()
    return get_profiles(db, version.id)


def _to_row(version_id: int, issue: DetectionIssue) -> DataIssue:
    indices = issue.affected_row_indices
    examples = [str(x) for x in issue.extra.get("examples", [])]
    details = {
        **issue.extra,
        "examples": examples,
        "row_indices": indices[:STORED_ROW_INDICES],
    }
    return DataIssue(
        version_id=version_id,
        row_index=indices[0] if indices else None,
        column_name=issue.column,
        issue_type=issue.issue_type,
        severity=issue.severity,
        current_value=examples[0] if examples else None,
        message=issue.message,
        status="open",
        affected_count=len(indices),
        details=details,
    )


def list_issue_rows(db: Session, version_id: int) -> list[DataIssue]:
    """Các dòng lỗi của phiên bản: nghiêm trọng nhất trước, rồi theo số dòng giảm dần."""
    rows = db.scalars(select(DataIssue).where(DataIssue.version_id == version_id)).all()
    return sorted(rows, key=lambda r: (_SEVERITY_ORDER.get(r.severity, 3), -r.affected_count, r.id))


def list_issues(db: Session, version_id: int) -> list[DataIssueOut]:
    """Lỗi của phiên bản (nghiêm trọng nhất trước, rồi theo số dòng); 404 nếu chưa profiling."""
    get_profiles_or_404(db, version_id)
    return [
        DataIssueOut(
            id=r.id,
            version_id=r.version_id,
            column_name=r.column_name,
            issue_type=r.issue_type,
            severity=r.severity,
            message=r.message,
            affected_count=r.affected_count,
            examples=list(r.details.get("examples", [])),
            kind=r.details.get("kind"),
            row_index=r.row_index,
            status=r.status,
            created_at=r.created_at,
        )
        for r in list_issue_rows(db, version_id)
    ]
