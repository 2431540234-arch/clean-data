"""Tính thống kê hệ thống: số user, dataset, lượt gọi AI, điểm chất lượng trung bình."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_request import AIRequest
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.user import User
from app.repositories import quality_repo
from app.schemas.admin import SystemStatsOut


def _count(db: Session, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0


def compute_system_stats(db: Session) -> SystemStatsOut:
    """Các số liệu thống kê hệ thống cho trang quản trị.

    total_ai_calls là số lần đã gọi AI thật (bảng ai_requests, cả thành công lẫn lỗi);
    average_quality_score là điểm 0-100 của các phiên bản hiện tại đã có báo cáo (0.0 nếu chưa có).
    """
    return SystemStatsOut(
        total_users=_count(db),
        total_admins=_count(db, User.role == "admin"),
        active_users=_count(db, User.is_active.is_(True)),
        total_projects=db.scalar(select(func.count()).select_from(Project)) or 0,
        total_datasets=db.scalar(select(func.count()).select_from(Dataset)) or 0,
        total_ai_calls=db.scalar(select(func.count()).select_from(AIRequest)) or 0,
        average_quality_score=quality_repo.average_score_all(db) or 0.0,
    )
