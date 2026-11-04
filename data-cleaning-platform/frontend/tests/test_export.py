"""Bước Xuất dữ liệu: file xuất của mock và trang chất lượng/tải xuống."""

import io

import pandas as pd
import pytest
import streamlit as st
from conftest import find_button

import api_client
from components import upload_rules
from components.quality_gauge import score_label

CONTEXT = {"work_context": {"dataset_id": 1}}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _downloads(at):
    return at.get("download_button")


# ---------------------------------------------------------------- nhãn điểm


@pytest.mark.parametrize(
    ("score", "label", "kind"),
    [
        (95, "Tốt", "success"),
        (80, "Tốt", "success"),
        (79.9, "Trung bình", "warning"),
        (60, "Trung bình", "warning"),
        (59.9, "Cần cải thiện", "error"),
        (0, "Cần cải thiện", "error"),
    ],
)
def test_score_label_thresholds(score, label, kind):
    assert score_label(score) == (label, kind)


# ---------------------------------------------------------------- API (mock)


def test_api_export_csv_has_bom_and_all_rows(call_api):
    content, error, _ = call_api("user", "export_csv", 1)
    assert error is None and isinstance(content, bytes)
    assert content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str)
    assert len(frame) == 30 and list(frame.columns)[0] == "ho_ten"


def test_api_export_excel_has_the_three_backend_sheets(call_api):
    content, error, _ = call_api("user", "export_excel", 1)
    assert error is None
    book = pd.ExcelFile(io.BytesIO(content))
    assert book.sheet_names == ["Dữ liệu", "Báo cáo chất lượng", "Lỗi đã phát hiện"]
    report = book.parse("Báo cáo chất lượng")
    assert list(report["Chỉ tiêu"])[0] == "Điểm chất lượng (0-100)"
    assert len(book.parse("Dữ liệu")) == 30
    issues = book.parse("Lỗi đã phát hiện")
    assert list(issues.columns) == ["Cột", "Loại lỗi", "Mức độ", "Số dòng", "Mô tả"]


@pytest.mark.parametrize(("method", "fmt"), [("export_csv", "csv"), ("export_excel", "xlsx")])
def test_api_export_writes_audit_entry_like_backend(call_api, method, fmt):
    content, error, db = call_api("user", method, 1)
    assert error is None
    entry = db["audit"][-1]
    assert entry["action"] == "dataset.export" and entry["entity_type"] == "dataset"
    assert entry["entity_id"] == 1
    assert entry["new_value"] == {"format": fmt, "version_number": 1, "bytes": len(content)}


def test_api_export_follows_current_version(call_api):
    steps = [{"op": "drop_duplicates", "column": None, "params": {}}]
    _, _, db = call_api("user", "apply_rules", 1, steps)
    content, error, _ = call_api("user", "export_csv", 2, state={"_mock_db": db})
    assert error is None
    assert len(pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")) == 29


def test_api_export_unknown_version_and_permissions(call_api):
    _, error, _ = call_api("user", "export_csv", 999)
    assert error.status_code == 404
    _, error, _ = call_api("admin", "export_excel", 1)
    assert error is None


# ---------------------------------------------------------------- trang


def test_page_shows_quality_and_components(run_view):
    at = run_view("export", role="user", state=CONTEXT)
    assert not at.exception
    picker = at.selectbox(key="export_version")
    assert picker.value == 1 and picker.label == "Phiên bản xuất"
    assert any("30 dòng × 6 cột" in c.value for c in at.caption)
    assert len(at.get("plotly_chart")) == 1  # gauge
    progress = [p.text for p in at.get("progress")]
    assert len(progress) == 4 and "Đầy đủ" in progress[0] and "trọng số 30%" in progress[0]
    html = " ".join(m.value for m in at.markdown)
    assert "/ 100" in html and "Tốt" in html  # 90,7 điểm
    assert any("phiên bản gốc, chưa làm sạch" in i.value for i in at.info)


def test_download_buttons_appear_only_after_creating_files(run_view):
    at = run_view("export", role="user", state=CONTEXT)
    assert not _downloads(at)
    find_button(at, "Tạo tệp CSV").click().run()
    assert len(_downloads(at)) == 1 and not at.exception
    find_button(at, "Tạo tệp Excel").click().run()
    buttons = _downloads(at)
    assert len(buttons) == 2
    labels = [b.proto.label for b in buttons]
    assert all(label.startswith("Tải xuống (") for label in labels)


def test_page_lists_exactly_the_sheets_the_backend_exports(run_view):
    at = run_view("export", role="user", state=CONTEXT)
    text = " ".join(m.value for m in at.markdown)
    for sheet in ("Dữ liệu", "Báo cáo chất lượng", "Lỗi đã phát hiện"):
        assert f"Sheet “{sheet}”" in text
    assert text.count("- Sheet “") == 3
    assert any(c.value == "3 sheet" for c in at.caption)


def test_download_file_name_follows_the_editable_name(run_view, monkeypatch):
    served = []
    original = st.download_button

    def spy(label, data=None, **kwargs):
        served.append({"data": data, **kwargs})
        return original(label, data=data, **kwargs)

    monkeypatch.setattr(st, "download_button", spy)
    at = run_view("export", role="user", state=CONTEXT)
    at.text_input(key="export_name_csv_1").set_value("khach_hang_sach.csv").run()
    find_button(at, "Tạo tệp CSV").click().run()
    csv = next(item for item in served if item["key"] == "download_csv")
    assert csv["file_name"] == "khach_hang_sach.csv" and csv["mime"] == "text/csv"
    assert csv["data"].startswith(b"\xef\xbb\xbf")  # UTF-8 có BOM


def test_export_history_comes_from_audit_log_of_this_dataset(run_view):
    at = run_view("export", role="user", state=CONTEXT)
    assert any("Chưa có lần xuất nào" in c.value for c in at.caption)
    find_button(at, "Tạo tệp CSV").click().run()
    find_button(at, "Tạo tệp Excel").click().run()
    history = next(d.value for d in at.dataframe if "Định dạng" in d.value.columns)
    assert list(history["Định dạng"]) == ["Excel", "CSV"]  # mới nhất trước
    assert set(history["Phiên bản"]) == {"v1"}


def test_version_picker_exports_a_chosen_older_version(run_view, call_api):
    steps = [{"op": "drop_duplicates", "column": None, "params": {}}]
    _, _, db = call_api("user", "apply_rules", 1, steps)
    at = run_view("export", role="user", state={**CONTEXT, "_mock_db": db})
    picker = at.selectbox(key="export_version")
    assert picker.value == 2 and picker.options[0].endswith("Hiện tại")
    picker.set_value(1).run()
    assert any("phiên bản gốc, chưa làm sạch" in i.value for i in at.info)
    find_button(at, "Tạo tệp CSV").click().run()
    assert at.session_state["work_context"]["exports"]["csv"]["version_id"] == 1
    entry = at.session_state["_mock_db"]["audit"][-1]
    assert entry["action"] == "dataset.export" and entry["new_value"]["version_number"] == 1


def test_exported_file_matches_download_content(run_view):
    at = run_view("export", role="user", state=CONTEXT)
    find_button(at, "Tạo tệp CSV").click().run()
    store = at.session_state["work_context"]["exports"]["csv"]
    assert store["version_id"] == 1 and store["content"].startswith(b"\xef\xbb\xbf")


def test_stale_file_hidden_when_version_changes(run_view, call_api):
    at = run_view("export", role="user", state=CONTEXT)
    find_button(at, "Tạo tệp CSV").click().run()
    steps = [{"op": "drop_duplicates", "column": None, "params": {}}]
    _, _, db = call_api(
        "user", "apply_rules", 1, steps, state={"_mock_db": at.session_state["_mock_db"]}
    )
    context = dict(at.session_state["work_context"])
    at2 = run_view("export", role="user", state={"work_context": context, "_mock_db": db})
    assert not _downloads(at2)  # file của phiên bản 1 không còn hiển thị
    assert at2.selectbox(key="export_version").value == 2  # mặc định phiên bản hiện tại
    assert not any("phiên bản gốc" in i.value for i in at2.info)


def test_quality_error_does_not_break_exports(run_view, monkeypatch):
    def boom(token, version_id):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "get_quality", boom)
    at = run_view("export", role="user", state=CONTEXT)
    assert not at.exception
    assert any("chưa sẵn sàng" in e.value for e in at.error)
    assert any(b.label == "Tạo tệp CSV" for b in at.button)  # vẫn xuất được


def test_export_failure_shown_inline(run_view, monkeypatch):
    at = run_view("export", role="user", state=CONTEXT)

    def refuse(token, version_id):
        raise api_client.APIError(422, "Không xuất được phiên bản này.")

    monkeypatch.setattr(api_client, "export_csv", refuse)
    find_button(at, "Tạo tệp CSV").click().run()
    assert any("Không xuất được phiên bản này." in e.value for e in at.error)
    assert not _downloads(at)


def test_page_without_dataset(run_view):
    at = run_view("export", role="user")
    assert any("Chưa chọn dataset" in m.value for m in at.markdown)


# ---------------------------------------------------------------- giới hạn dòng của Excel


def test_excel_is_blocked_with_a_hint_when_rows_exceed_one_sheet(run_view, monkeypatch):
    monkeypatch.setattr(upload_rules, "EXCEL_MAX_DATA_ROWS", 20)  # dataset mẫu có 30 dòng
    at = run_view("export", role="user", state=CONTEXT)
    assert not at.exception
    assert find_button(at, "Tạo tệp Excel").disabled
    assert not find_button(at, "Tạo tệp CSV").disabled  # CSV không giới hạn số dòng
    warning = " ".join(w.value for w in at.warning)
    assert "30 dòng" in warning and "20 dòng" in warning and "xuất CSV" in warning
    assert "không tự cắt" in warning


def test_excel_is_available_at_exactly_the_limit(run_view, monkeypatch):
    monkeypatch.setattr(upload_rules, "EXCEL_MAX_DATA_ROWS", 30)
    at = run_view("export", role="user", state=CONTEXT)
    assert not find_button(at, "Tạo tệp Excel").disabled
    assert not any("giới hạn" in w.value for w in at.warning)


def test_mock_excel_export_refuses_rows_over_the_limit_like_the_backend(call_api, monkeypatch):
    monkeypatch.setattr(upload_rules, "EXCEL_MAX_DATA_ROWS", 20)
    _, error, _ = call_api("user", "export_excel", 1)
    assert error.status_code == 422 and "xuất CSV" in error.detail
    content, error, _ = call_api("user", "export_csv", 1)
    assert error is None and len(pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")) == 30


def test_real_excel_limit_message_uses_vietnamese_number_format():
    assert upload_rules.excel_row_problem(1_048_575) is None
    message = upload_rules.excel_row_problem(1_048_576)
    assert "1.048.576" in message and "1.048.575" in message and "CSV" in message


def test_export_history_shows_excel_for_the_backend_format_code_xlsx(run_view):
    at = run_view("export", role="user", state=CONTEXT)
    find_button(at, "Tạo tệp Excel").click().run()
    history = next(d.value for d in at.dataframe if "Định dạng" in d.value.columns)
    assert list(history["Định dạng"]) == ["Excel"]
