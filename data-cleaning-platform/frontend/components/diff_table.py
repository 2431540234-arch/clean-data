"""Bảng hiển thị dữ liệu trước/sau khi áp dụng rule, tô màu các ô bị thay đổi."""

from typing import Any

import pandas as pd
import streamlit as st

from components.formatting import format_number
from components.ui import data_table

_HIGHLIGHT = "background-color: #fef3c7; color: #92400e; font-weight: 600"
_DELETED = "background-color: #fee2e2; color: #991b1b; font-weight: 700"
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


def _after_to_before_rows(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    diffs: list[dict[str, Any]] | None,
) -> list[int] | None:
    """Ghép thứ tự các dòng sau với dòng gốc; trả None nếu không thể đối chiếu."""
    before, after = _frame(before_rows), _frame(after_rows)
    if diffs is None:
        return None
    shared = [c for c in after.columns if c in before.columns]

    expected = before[shared].copy().astype(str)
    for diff in diffs:
        if diff["column"] in shared:
            expected.at[diff["row_index"], diff["column"]] = str(diff["after"] or "")

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
    return mapping


def deleted_before_rows(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    diffs: list[dict[str, Any]] | None,
) -> set[int] | None:
    """Chỉ số các dòng gốc không còn trong dữ liệu sau."""
    mapping = _after_to_before_rows(before_rows, after_rows, diffs)
    if mapping is None:
        return None
    retained = set(mapping)
    return set(range(len(before_rows))) - retained


def changed_cells(
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    diffs: list[dict[str, Any]] | None,
) -> set[tuple[int, str]] | None:
    """Tập (vị trí dòng trong `after_rows`, tên cột) của các ô thay đổi."""
    before, after = _frame(before_rows), _frame(after_rows)
    mapping = _after_to_before_rows(before_rows, after_rows, diffs)
    if mapping is None:
        return None
    shared = [c for c in after.columns if c in before.columns]
    new_columns = [c for c in after.columns if c not in before.columns]
    cells_by_before_row: dict[int, set[str]] = {}
    for diff in diffs or []:
        if diff["column"] in shared:
            cells_by_before_row.setdefault(diff["row_index"], set()).add(diff["column"])

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
        deleted = deleted_before_rows(before_rows, after_rows, diffs)
        if deleted is None:
            st.caption("Không xác định được chính xác các dòng đã bị xóa.")
            data_table(before, height=360)
        else:
            marked_before = before.copy()
            marked_before.insert(
                0,
                "Trạng thái",
                ["Bị xóa" if index in deleted else "" for index in range(len(before))],
            )
            st.caption("Dòng có nhãn “Bị xóa” đã bị loại khỏi dữ liệu sau.")
            styled_before = marked_before.style.apply(
                lambda frame: pd.DataFrame(
                    [
                        [_DELETED if index in deleted else "" for _ in frame.columns]
                        for index in range(len(frame))
                    ],
                    index=frame.index,
                    columns=frame.columns,
                ),
                axis=None,
            )
            st.dataframe(
                styled_before,
                use_container_width=True,
                hide_index=True,
                height=360,
            )
