"""Op chuẩn hóa định dạng ngày tháng."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("standardize_date")
def standardize_date(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Chuẩn hóa cột ngày về một định dạng thống nhất (mặc định ISO yyyy-mm-dd).

    params:
        output_format: chuỗi định dạng đích, mặc định "%Y-%m-%d".
        dayfirst: bool, True nếu dữ liệu nguồn ưu tiên dd/mm/yyyy (mặc định True cho VN).

    Gợi ý cách làm: dùng dateutil.parser.parse với dayfirst=params.get("dayfirst", True)
    để xử lý dữ liệu lẫn cả dd/mm/yyyy và yyyy-mm-dd, sau đó format lại theo output_format.
    """
    raise NotImplementedError(
        "TODO: parse từng giá trị bằng dateutil.parser.parse(dayfirst=...), "
        "format lại theo params['output_format'], đếm số dòng thay đổi/parse lỗi."
    )
