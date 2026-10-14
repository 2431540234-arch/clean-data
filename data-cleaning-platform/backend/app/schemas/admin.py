"""Schema thống kê hệ thống dành cho trang quản trị (chỉ admin)."""

from pydantic import BaseModel


class SystemStatsOut(BaseModel):
    """Thống kê tổng quan: số user, dataset, lượt gọi AI, điểm chất lượng trung bình."""

    total_users: int
    total_admins: int
    active_users: int
    total_projects: int
    total_datasets: int
    total_ai_calls: int
    average_quality_score: float
