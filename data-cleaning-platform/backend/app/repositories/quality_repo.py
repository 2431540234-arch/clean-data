"""Truy vấn DB cho bảng quality_reports (mỗi phiên bản tối đa một báo cáo)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.project import Project
from app.models.quality_report import QualityReport
from app.services.quality import QualityMetrics


def get_for_version(db: Session, version_id: int) -> QualityReport | None:
    return db.scalars(select(QualityReport).where(QualityReport.version_id == version_id)).first()


def save(db: Session, version_id: int, metrics: QualityMetrics) -> QualityReport:
    """Lưu báo cáo (flush, người gọi tự commit)."""
    report = QualityReport(
        version_id=version_id,
        overall_score=metrics.overall_score,
        completeness=metrics.completeness,
        uniqueness=metrics.uniqueness,
        validity=metrics.validity,
        consistency=metrics.consistency,
        issue_summary=metrics.issue_summary,
    )
    db.add(report)
    db.flush()
    return report


def average_score_by_project(db: Session, project_ids: list[int]) -> dict[int, float]:
    """Điểm trung bình (1 chữ số thập phân) của phiên bản HIỆN TẠI các dataset, theo project.

    Chỉ tính các phiên bản đã có báo cáo; project chưa có báo cáo nào không xuất hiện trong kết quả.
    """
    if not project_ids:
        return {}
    rows = db.execute(
        select(Dataset.project_id, func.avg(QualityReport.overall_score))
        .join(QualityReport, QualityReport.version_id == Dataset.current_version_id)
        .where(Dataset.project_id.in_(project_ids))
        .group_by(Dataset.project_id)
    )
    return {project_id: round(float(avg), 1) for project_id, avg in rows}


def average_score_all(db: Session) -> float | None:
    """Điểm trung bình toàn hệ thống (phiên bản hiện tại của mọi dataset có báo cáo)."""
    value = db.scalar(
        select(func.avg(QualityReport.overall_score))
        .join(Dataset, Dataset.current_version_id == QualityReport.version_id)
        .join(Project, Project.id == Dataset.project_id)
    )
    return round(float(value), 1) if value is not None else None
