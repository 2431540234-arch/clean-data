"""Bảng hiển thị dữ liệu trước/sau khi áp dụng rule, tô màu các ô bị thay đổi."""

from typing import Any

import pandas as pd
import streamlit as st

from components.formatting import format_number
from components.ui import data_table

_HIGHLIGHT = "background-color: #fef3c7; color: #92400e; font-weight: 600"
_MAX_DIFF_ROWS = 500
_EMPTY = "(trống)"


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _visible(value: Any) -> str:
    """Giá trị để hiển thị: rỗng -> "(trống)", thừa khoảng trắng đầu/cuối -> đặt trong dấu nháy."""
    if value is None or value == "":
        return _EMPTY
    text = str(value)
    return f'"{text}"' if text != text.strip() else text


def changed_cells(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    diffs: list[dict[str, Any]] | None,
) -> set[tuple[int, str]] | None:
    """Tập (vị trí dòng trong `after_rows`, tên cột) của các ô thay đổi; cột mới coi là đổi hết.

    Dòng trong `after_rows` không có chỉ số gốc, nên ghép với `before_rows` bằng cách áp các `diffs`
    lên dòng "trước" rồi khớp theo thứ tự (các dòng còn lại là dãy con, dòng bị xóa bị bỏ qua).

    Returns:
        None nếu không ghép được (không có diffs hoặc kết quả không khớp dãy con).
    """
    before, after = _frame(before_rows), _frame(after_rows)
    if diffs is None:
        return None
    shared = [c for c in after.columns if c in before.columns]
    new_columns = [c for c in after.columns if c not in before.columns]

    expected = before[shared].copy().astype(str)
    cells_by_before_row: dict[int, set[str]] = {}
    for diff in diffs:
        if diff["column"] in shared:
            expected.at[diff["row_index"], diff["column"]] = str(diff["after"] or "")
            cells_by_before_row.setdefault(diff["row_index"], set()).add(diff["column"])

    expected_rows = expected.to_numpy().tolist()
    after_values = after[shared].astype(str).to_numpy().tolist()
    mapping: list[int] = []
    position = 0
    for index, row in enumerate(expected_rows):
        if position < len(after_values) and row == after_values[position]:
            mapping.append(index)
            position += 1
    if position != len(after_values):
        return None

    cells: set[tuple[int, str]] = set()
    for after_position, before_index in enumerate(mapping):
        cells |= {(after_position, c) for c in cells_by_before_row.get(before_index, set())}
        cells |= {(after_position, c) for c in new_columns}
    return cells


def _shape_summary(before: pd.DataFrame, after: pd.DataFrame) -> str:
    parts = [f"Số dòng: {len(before)} → {len(after)}"]
    if len(after) < len(before):
        parts[0] += f" (xóa {len(before) - len(after)} dòng)"
    added = [c for c in after.columns if c not in before.columns]
    removed = [c for c in before.columns if c not in after.columns]
    if added:
        parts.append("Cột mới: " + ", ".join(f"“{c}”" for c in added))
    if removed:
        parts.append("Cột không còn: " + ", ".join(f"“{c}”" for c in removed))
    return " · ".join(parts)


def render_diff_table(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    diffs: list[dict[str, Any]] | None = None,
) -> None:
    """Hiển thị kết quả xem trước: danh sách thay đổi theo ô và bảng trước/sau có tô màu.

    Args:
        before_rows / after_rows: mẫu dữ liệu trước và sau (PreviewResult).
        diffs: danh sách ColumnDiff {row_index, column, before, after}.
    """
    before, after = _frame(before_rows), _frame(after_rows)
    st.caption(_shape_summary(before, after))

    tab_cells, tab_after, tab_before = st.tabs(["Thay đổi theo ô", "Dữ liệu sau", "Dữ liệu trước"])
    with tab_cells:
        if diffs:
            shown = diffs[:_MAX_DIFF_ROWS]
            if len(diffs) > _MAX_DIFF_ROWS:
                st.caption(
                    f"Hiển thị {_MAX_DIFF_ROWS}/{format_number(len(diffs))} thay đổi đầu tiên."
                )
            table = pd.DataFrame(
                {
                    "Dòng": [d["row_index"] + 1 for d in shown],
                    "Cột": [d["column"] for d in shown],
                    "Trước": [_visible(d["before"]) for d in shown],
                    "Sau": [_visible(d["after"]) for d in shown],
                }
            )
            data_table(table, height=min(420, 56 + 36 * len(table)))
        else:
            st.info("Không có ô nào đổi giá trị.", icon=":material/info:")

    with tab_after:
        cells = changed_cells(before_rows, after_rows, diffs)
        if cells is None:
            st.caption("Không đối chiếu được từng ô; xem tab “Thay đổi theo ô”.")
            data_table(after, height=360)
        else:
            st.caption("Ô được tô màu là ô có giá trị thay đổi so với trước.")
            styled = after.style.apply(
                lambda frame: pd.DataFrame(
                    [
                        [_HIGHLIGHT if (r, c) in cells else "" for c in frame.columns]
                        for r in range(len(frame))
                    ],
                    index=frame.index,
                    columns=frame.columns,
                ),
                axis=None,
            )
            st.dataframe(styled, use_container_width=True, hide_index=True, height=360)
    with tab_before:
        data_table(before, height=360)
