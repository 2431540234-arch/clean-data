"""Bước Tổng quan dữ liệu: profiling/chất lượng của mock và trang hiển thị."""

import pytest
import streamlit as st
from conftest import find_button

import api_client
import mock_data
import mock_profiling
from components import dataset_context

CONTEXT = {"work_context": {"dataset_id": 1}}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


# ---------------------------------------------------------------- mock_profiling


@pytest.fixture(scope="module")
def sample():
    frame = mock_data.sample_frame()
    columns = {c["column_name"]: c for c in mock_profiling.profile_frame(frame, 1, 1, "now")}
    return frame, columns


def test_profile_infers_types_of_sample_data(sample):
    _, columns = sample
    assert {name: c["inferred_type"] for name, c in columns.items()} == {
        "ho_ten": "text",
        "email": "email",
        "so_dien_thoai": "phone",
        "ngay_sinh": "date",
        "tuoi": "integer",
        "tinh_thanh": "text",
    }


def test_profile_counts_nulls_including_null_tokens(sample):
    _, columns = sample
    assert columns["email"]["null_count"] == 1
    assert columns["tuoi"]["null_count"] == 4  # '-' và ô trống
    assert columns["tinh_thanh"]["null_count"] == 2  # ô trống và 'N/A'
    assert columns["tuoi"]["null_ratio"] == pytest.approx(4 / 30)


def test_profile_numeric_stats_and_formats(sample):
    _, columns = sample
    age = columns["tuoi"]
    assert (age["min_value"], age["max_value"]) == ("-5", "150")
    assert age["mean_value"] == pytest.approx(35.23, abs=0.01)
    assert columns["ho_ten"]["min_value"] is None
    assert "Nhiều định dạng" in columns["ngay_sinh"]["detected_format"]
    assert len(columns["email"]["sample_values"]) == 5


def test_profile_matches_schema_fields(sample):
    _, columns = sample
    expected = {
        "id", "version_id", "column_name", "column_index", "inferred_type", "null_count",
        "unique_count", "null_ratio", "unique_ratio", "min_value", "max_value", "mean_value",
        "sample_values", "detected_format", "created_at",
    }  # fmt: skip
    assert set(columns["email"]) == expected


def test_quality_follows_documented_formula(sample):
    frame, _ = sample
    report = mock_profiling.quality_report(frame, 1, 1, "now")
    expected = 100 * sum(
        mock_profiling.WEIGHTS[name] * report[name] for name in mock_profiling.WEIGHTS
    )
    assert report["overall_score"] == pytest.approx(expected, abs=0.1)
    assert report["uniqueness"] < 1 and report["completeness"] < 1  # có dòng trùng và ô thiếu
    assert report["issue_summary"]["duplicate_rows"] == 1


def test_clean_frame_scores_perfect():
    import pandas as pd

    frame = pd.DataFrame({"a": ["x", "y", "z"], "b": ["1", "2", "3"]})
    assert mock_profiling.quality_report(frame, 1, 1, "now")["overall_score"] == 100.0


# ---------------------------------------------------------------- API


def test_profiling_get_404_until_run(call_api):
    _, error, db = call_api("user", "get_profiling", 1)
    assert error.status_code == 404
    result, error, db = call_api("user", "run_profiling", 1, state={"_mock_db": db})
    assert error is None and result["version_id"] == 1 and len(result["columns"]) == 6
    result, error, _ = call_api("user", "get_profiling", 1, state={"_mock_db": db})
    assert error is None and len(result["columns"]) == 6


def test_quality_endpoint_and_unknown_version(call_api):
    report, error, _ = call_api("user", "get_quality", 1)
    assert error is None and 0 <= report["overall_score"] <= 100
    _, error, _ = call_api("user", "get_quality", 999)
    assert error.status_code == 404


# ---------------------------------------------------------------- Trang


def test_page_without_dataset_shows_empty_state(run_view):
    at = run_view("overview", role="user")
    assert not at.exception
    assert any("Chưa chọn dataset" in m.value for m in at.markdown)


def test_page_runs_profiling_automatically_and_shows_stats(run_view):
    at = run_view("overview", role="user", state=CONTEXT)
    assert not at.exception
    assert 1 in at.session_state["_mock_db"]["profiles"]  # chưa có -> tự chạy
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Số dòng"] == "30" and metrics["Số cột"] == "6"
    assert metrics["Điểm chất lượng"].endswith("/ 100")
    assert [t.label for t in at.tabs] == ["Thống kê cột", "Lỗi đã phát hiện", "Biểu đồ"]
    table = at.dataframe[0].value
    assert list(table["Cột"]) == [
        "ho_ten", "email", "so_dien_thoai", "ngay_sinh", "tuoi", "tinh_thanh",
    ]  # fmt: skip
    assert table.loc[table["Cột"] == "tuoi", "Lưu ý"].item() == "Thiếu nhiều"
    assert table.loc[table["Cột"] == "email", "Lưu ý"].item() == ""
    assert any(b.label == "Tiếp tục: Mapping cột" for b in at.button)


def test_page_column_detail_selector(run_view):
    at = run_view("overview", role="user", state=CONTEXT)
    at.selectbox(key="overview_column").set_value("tuoi").run()
    values = {m.label: m.value for m in at.metric}
    assert values["Kiểu dữ liệu"] == "Số nguyên"
    assert values["Giá trị thiếu"] == "4 (13,3%)"


def test_page_rerun_button_recomputes_profile(run_view):
    at = run_view("overview", role="user", state=CONTEXT)
    first_ids = [c["id"] for c in at.session_state["_mock_db"]["profiles"][1]]
    find_button(at, "Phân tích lại").click().run()
    new_ids = [c["id"] for c in at.session_state["_mock_db"]["profiles"][1]]
    assert new_ids != first_ids and not at.exception


def test_page_api_error_shows_friendly_state(run_view, monkeypatch):
    def boom(token, version_id):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(dataset_context, "get_profiling", boom)
    at = run_view("overview", role="user", state=CONTEXT)
    assert not at.exception
    assert any("chưa sẵn sàng" in e.value for e in at.error)
    assert any(b.label == "Thử lại" for b in at.button)


def test_page_quality_failure_does_not_block(run_view, monkeypatch):
    def boom(token, version_id):
        raise api_client.APIError(500, "lỗi")

    monkeypatch.setattr(api_client, "get_quality", boom)
    at = run_view("overview", role="user", state=CONTEXT)
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Điểm chất lượng"] == "—"


def test_distribution_chart_renders_nothing_without_data():
    from streamlit.testing.v1 import AppTest

    def app():
        from components.charts import render_distribution_chart

        render_distribution_chart([], "tuoi")
        render_distribution_chart([None, ""], "tuoi")

    at = AppTest.from_function(app, default_timeout=30).run()
    assert not at.exception and len(at.main) == 0


def test_distribution_chart_draws_numbers_and_categories():
    from streamlit.testing.v1 import AppTest

    def app():
        from components.charts import render_distribution_chart

        render_distribution_chart(["1", "2", "2", "3"], "tuoi")
        render_distribution_chart(["Ha Noi", "Ha Noi", "Da Nang"], "tinh")

    at = AppTest.from_function(app, default_timeout=30).run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 2  # một histogram, một biểu đồ thanh
