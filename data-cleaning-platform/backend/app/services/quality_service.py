"""Lấy (hoặc tính rồi lưu) báo cáo chất lượng của một phiên bản."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dataset import DatasetVersion
from app.models.quality_report import QualityReport
from app.repositories import quality_repo
from app.services import profiling_service
from app.services.detectors import run_all_detectors
from app.services.frames import load_version_frame
from app.services.quality import compute_quality_score


def get_or_compute(db: Session, version: DatasetVersion) -> QualityReport:
    """Báo cáo đã lưu của phiên bản; chưa có thì tính và lưu (phiên bản bất biến nên cache được)."""
    report = quality_repo.get_for_version(db, version.id)
    if report is not None:
        return report

    profiles = profiling_service.get_profiles(db, version.id)
    if not profiles:
        # Chưa profiling: chạy luôn (lưu cả cột, lỗi và điểm chất lượng trong một lần).
        profiling_service.run_profiling(db, version)
    else:
        # Đã profiling từ trước nhưng chưa có điểm: chỉ cần tính điểm.
        frame = load_version_frame(version)
        types = {p.column_name: p.inferred_type for p in profiles}
        metrics = compute_quality_score(frame, run_all_detectors(frame, types), types)
        try:
            quality_repo.save(db, version.id, metrics)
            db.commit()
        except IntegrityError:  # request khác vừa lưu xong: dùng bản của họ
            db.rollback()
    report = quality_repo.get_for_version(db, version.id)
    assert report is not None
    return report
