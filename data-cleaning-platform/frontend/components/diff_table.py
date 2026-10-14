"""Bảng hiển thị dữ liệu trước/sau khi áp dụng rule, tô màu các ô bị thay đổi."""

from typing import Any


def render_diff_table(before_rows: list[dict[str, Any]], after_rows: list[dict[str, Any]]) -> None:
    """Hiển thị bảng trước/sau, tô màu nền các ô có giá trị thay đổi.

    Gợi ý cách làm: dùng pandas.DataFrame.style.apply để tô màu theo mask so sánh
    before/after, hiển thị bằng st.dataframe hoặc st.write(df.style...).
    """
    raise NotImplementedError("TODO: render bảng diff trước/sau có tô màu ô thay đổi.")
