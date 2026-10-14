"""Sinh báo cáo chất lượng dữ liệu (dùng khi export kèm báo cáo, hoặc xem trên dashboard)."""

import pandas as pd

from app.schemas.quality import QualityReportOut


def build_quality_report_dataframe(
    score: QualityReportOut, issues_summary: list[dict]
) -> pd.DataFrame:
    """Dựng DataFrame báo cáo chất lượng để xuất kèm file Excel (sheet "Bao cao").

    Gợi ý cách làm: tạo bảng gồm các dòng: điểm tổng, điểm từng tiêu chí (từ score.metrics),
    và danh sách lỗi đã phát hiện/đã xử lý (từ issues_summary).
    """
    raise NotImplementedError("TODO: dựng DataFrame báo cáo chất lượng từ score và issues_summary.")
