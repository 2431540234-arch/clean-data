"""Bước Xuất dữ liệu: file xuất của mock và trang chất lượng/tải xuống."""

import io

import pandas as pd
import pytest
import streamlit as st
from conftest import find_button

import api_client
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


def test_api_export_excel_has_data_and_quality_sheets(call_api):
    content, error, _ = call_api("user", "export_excel", 1)
    assert error is None
    book = pd.ExcelFile(io.BytesIO(content))
    assert book.sheet_names == ["Dữ liệu", "Báo cáo chất lượng"]
    report = book.parse("Báo cáo chất lượng")
    assert list(report["Chỉ tiêu"])[0] == "Điểm chất lượng (0-100)"
    assert len(book.parse("Dữ liệu")) == 30


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
    assert {m.label: m.value for m in at.metric} == {
        "Phiên bản xuất": "Phiên bản 1",
        "Số dòng": "30",
        "Số cột": "6",
    }
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
    assert {m.label: m.value for m in at2.metric}["Phiên bản xuất"] == "Phiên bản 2"
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
