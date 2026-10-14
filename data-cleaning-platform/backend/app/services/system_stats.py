"""Tính thống kê hệ thống: số user, dataset, lượt gọi AI, điểm chất lượng trung bình."""

from sqlalchemy.orm import Session

from app.schemas.admin import SystemStatsOut


def compute_system_stats(db: Session) -> SystemStatsOut:
    """Tính toán các số liệu thống kê hệ thống cho trang quản trị.

    Gợi ý cách làm: dùng các câu lệnh COUNT/AVG trên users, projects, datasets,
    suggestions (where source='ai' để đếm lượt gọi AI), quality_reports.
    """
    raise NotImplementedError("TODO: tính thống kê hệ thống từ các bảng DB liên quan.")
