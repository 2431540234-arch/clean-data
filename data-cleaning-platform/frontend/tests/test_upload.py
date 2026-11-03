"""Bước Tải lên: hợp đồng API upload (qua mock, file thật), trang Tải lên và thanh ngữ cảnh."""

import io
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from conftest import find_button

import mock_api

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _upload(call_api, name, content, project_id=1, role="user"):
    return call_api(role, "upload_dataset", project_id, name, content, None)


def _multi_sheet_xlsx() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"ten": ["An", "Bình"], "tuoi": ["30", "25"]}).to_excel(
            writer, sheet_name="NhanVien", index=False
        )
        pd.DataFrame({"ma": ["A1", "B2", "C3"]}).to_excel(writer, sheet_name="DanhMuc", index=False)
    return buffer.getvalue()


# ---------------------------------------------------------------- API (mock, file thật)


def test_upload_csv_returns_schema_shaped_response(call_api):
    content = (FIXTURES / "cp1258_sample.csv").read_bytes()
    result, error, db = _upload(call_api, "khach_hang.csv", content)
    assert error is None
    dataset, version = result["dataset"], result["first_version"]
    assert dataset["original_filename"] == "khach_hang.csv" and dataset["project_id"] == 1
    assert dataset["current_version_id"] == version["id"] and version["version_number"] == 1
    assert version["column_count"] == 6 and version["row_count"] > 0
    assert result["sheet_names"] == []
    first = result["preview_rows"][0]
    assert first["row_index"] == 0 and "ho_ten" in first["values"]
    assert any(d["id"] == dataset["id"] for d in db["datasets"])


def test_upload_excel_single_sheet(call_api):
    result, error, _ = _upload(
        call_api, "nhan_su.xlsx", (FIXTURES / "dirty_sample.xlsx").read_bytes()
    )
    assert error is None
    assert result["sheet_names"] == ["Sheet1"] and result["dataset"]["sheet_name"] == "Sheet1"
    assert result["dataset"]["encoding"] is None


def test_upload_empty_cells_become_none_in_preview(call_api):
    result, _, _ = _upload(call_api, "a.csv", b"ho_ten,email\nAn,\n")
    assert result["preview_rows"][0]["values"] == {"ho_ten": "An", "email": None}


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("anh.png", b"\x89PNG", "Định dạng file không được hỗ trợ"),
        ("rong.csv", b"", "không đọc được"),
        ("chi_tieu_de.csv", b"a,b,c\n", "File không có dữ liệu"),
    ],
)
def test_upload_rejects_bad_files(call_api, name, content, message):
    _, error, _ = _upload(call_api, name, content)
    assert error is not None and error.status_code == 422
    assert message.lower() in error.detail.lower()


def test_upload_to_someone_elses_project_is_forbidden(call_api):
    _, error, _ = _upload(call_api, "a.csv", b"a\n1\n", project_id=3)  # project của admin
    assert error.status_code == 403


def test_select_sheet_rereads_sheet_and_validates(call_api):
    result, _, db = _upload(call_api, "nhieu_sheet.xlsx", _multi_sheet_xlsx())
    assert result["sheet_names"] == ["NhanVien", "DanhMuc"]
    dataset_id = result["dataset"]["id"]

    switched, error, db = call_api(
        "user", "select_sheet", dataset_id, "DanhMuc", state={"_mock_db": db}
    )
    assert error is None
    assert switched["dataset"]["sheet_name"] == "DanhMuc"
    assert (
        switched["first_version"]["row_count"] == 3
        and switched["first_version"]["column_count"] == 1
    )

    _, error, _ = call_api("user", "select_sheet", dataset_id, "KhongCo", state={"_mock_db": db})
    assert error.status_code == 422


def test_seed_dataset_is_readable_and_versions_listed(call_api):
    dataset, error, _ = call_api("user", "get_dataset", 1)
    assert error is None and dataset["original_filename"] == "khach_hang_ban.csv"
    versions, error, _ = call_api("user", "list_dataset_versions", 1)
    assert error is None and [v["version_number"] for v in versions] == [1]
    _, error, _ = call_api("admin", "get_dataset", 1)  # admin xem được
    assert error is None


# ---------------------------------------------------------------- Trang Tải lên


def test_upload_page_initial_state(run_view):
    at = run_view("upload", role="user")
    assert not at.exception
    assert at.title[0].value == "Tải lên"
    assert at.selectbox[0].label == "Project"  # ô chọn project để tải lên
    assert any(b.label == "Tải lên" and b.disabled for b in at.button)  # chưa chọn file
    assert any("tối đa 50 MB" in c.value for c in at.caption)


def test_upload_page_without_projects_guides_user(run_view):
    db = mock_api._seed()
    db["projects"] = []
    at = run_view("upload", role="user", state={"_mock_db": db})
    assert any("Bạn chưa có project nào" in m.value for m in at.markdown)
    assert any(b.label.startswith("Đến Dashboard") for b in at.button)


def test_upload_page_shows_result_with_preview(run_view, call_api):
    result, _, db = _upload(
        call_api, "khach_hang.csv", (FIXTURES / "cp1258_sample.csv").read_bytes()
    )
    at = run_view(
        "upload", role="user", state={"_mock_db": db, "work_context": {"upload_result": result}}
    )
    assert not at.exception
    assert any("Đã tải lên “khach_hang.csv”" in s.value for s in at.success)
    assert {m.label for m in at.metric} == {"Số dòng", "Số cột", "Dung lượng", "Encoding"}
    assert len(at.dataframe) == 1
    assert any(b.label == "Tiếp tục: Tổng quan dữ liệu" for b in at.button)


def test_upload_page_excel_sheet_picker(run_view, call_api):
    result, _, db = _upload(call_api, "nhieu_sheet.xlsx", _multi_sheet_xlsx())
    at = run_view(
        "upload", role="user", state={"_mock_db": db, "work_context": {"upload_result": result}}
    )
    assert "Sheet" in [s.label for s in at.selectbox]
    at.selectbox(key=f"sheet_{result['dataset']['id']}").set_value("DanhMuc").run()
    find_button(at, "Dùng sheet này").click().run()
    assert at.session_state["work_context"]["upload_result"]["dataset"]["sheet_name"] == "DanhMuc"


# ---------------------------------------------------------------- Thanh ngữ cảnh dataset


def _bar_app():
    from components.dataset_context import dataset_context_bar

    active = dataset_context_bar()
    import streamlit as st

    st.session_state["_active"] = (active.dataset["id"], active.version["version_number"])


def _run_bar(role, context):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_bar_app, default_timeout=30)
    at.session_state["access_token"] = "mock-token-2" if role == "user" else "mock-token-1"
    at.session_state["work_context"] = context
    return at.run()


def test_context_bar_without_dataset_shows_empty_state_and_open_form():
    at = _run_bar("user", {})
    assert not at.exception and "_active" not in at.session_state
    assert any("Chưa chọn dataset" in m.value for m in at.markdown)
    assert any(b.label == "Tải dữ liệu lên" for b in at.button)


def test_context_bar_shows_active_dataset():
    at = _run_bar("user", {"dataset_id": 1, "project_name": "Khách hàng 2026"})
    assert not at.exception
    assert at.session_state["_active"] == (1, 1)
    assert any("khach_hang_ban.csv" in m.value and "Phiên bản 1" in m.value for m in at.markdown)
    assert at.session_state["work_context"]["version_id"] == 1


def test_context_bar_clears_inaccessible_dataset():
    at = _run_bar("user", {"dataset_id": 999})
    assert any("Không mở được dataset #999" in w.value for w in at.warning)
    assert at.session_state["work_context"]["dataset_id"] is None


def test_open_dataset_from_list_sets_context():
    at = _run_bar("user", {})
    # danh sách dataset của project đang chọn (project đầu tiên: "Khách hàng 2026")
    assert at.selectbox(key="ctx_open_empty_project").value == 1  # "Khách hàng 2026"
    dataset_box = at.selectbox(key="ctx_open_empty_dataset_1")
    assert dataset_box.options == ["khach_hang_ban.csv (#1)"]
    at.button(key="ctx_open_empty_open").click().run()
    context = at.session_state["work_context"]
    assert context["dataset_id"] == 1 and context["dataset_name"] == "khach_hang_ban.csv"
    assert context["project_name"] == "Khách hàng 2026"


def test_open_dataset_picker_handles_project_without_datasets():
    at = _run_bar("user", {})
    at.selectbox(key="ctx_open_empty_project").set_value(2).run()  # "Đơn hàng quý 3"
    assert any("chưa có dataset nào" in i.value for i in at.info)
    assert not [b for b in at.button if b.key == "ctx_open_empty_open"]


def test_context_bar_fetches_project_name_when_missing():
    at = _run_bar("user", {"dataset_id": 1})
    assert any("Khách hàng 2026" in c.value for c in at.caption)
    assert at.session_state["work_context"]["project_name"] == "Khách hàng 2026"
