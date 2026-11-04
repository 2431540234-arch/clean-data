"""Bước Gợi ý làm sạch: API (mock) và trang (sinh gợi ý, duyệt, xem trước, áp dụng)."""

import pytest
import streamlit as st
from conftest import find_button

import api_client

CONTEXT = {"work_context": {"dataset_id": 1}}
E164_PHONE = "+84901234567"


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _step(op, column=None, **params):
    return {"op": op, "column": column, "params": params}


# ---------------------------------------------------------------- API


def test_api_generate_list_and_decide(call_api):
    created, error, db = call_api("user", "generate_suggestions", 1)
    assert error is None and len(created) == 8
    first = created[0]
    assert first["status"] == "pending" and first["version_id"] == 1
    assert first["proposed_rule"]["steps"][0]["op"] == "drop_duplicates"

    listed, error, db = call_api("user", "list_suggestions", 1, state={"_mock_db": db})
    assert error is None and [s["id"] for s in listed] == [s["id"] for s in created]

    decided, error, db = call_api(
        "user", "decide_suggestion", first["id"], "accepted", state={"_mock_db": db}
    )
    assert error is None and decided["status"] == "accepted" and decided["reviewed_by"] == 2

    _, error, _ = call_api(
        "user", "decide_suggestion", first["id"], "maybe", state={"_mock_db": db}
    )
    assert error.status_code == 422


def test_api_generate_replaces_previous_suggestions(call_api):
    _, _, db = call_api("user", "generate_suggestions", 1)
    again, _, db = call_api("user", "generate_suggestions", 1, state={"_mock_db": db})
    listed, _, _ = call_api("user", "list_suggestions", 1, state={"_mock_db": db})
    assert len(listed) == len(again) == 8


def test_api_preview_does_not_change_data(call_api):
    result, error, db = call_api(
        "user", "preview_rules", 1, [_step("trim_whitespace", "email")], 50
    )
    assert error is None and result["version_id"] == 1
    assert result["affected_row_count"] == 4 and len(result["diffs"]) == 4
    assert len(db["versions"]) == 1  # xem trước không tạo version


def test_api_preview_rejects_bad_rules(call_api):
    _, error, _ = call_api("user", "preview_rules", 1, [_step("exec_code", "email")], 50)
    assert error.status_code == 422 and "không được hỗ trợ" in error.detail
    _, error, _ = call_api("user", "preview_rules", 1, [_step("trim_whitespace", "khong_co")], 50)
    assert error.status_code == 422 and "không tồn tại" in error.detail


def test_api_apply_creates_new_current_version(call_api):
    steps = [_step("drop_duplicates"), _step("rename_column", "email", new_name="thu_dien_tu")]
    version, error, db = call_api("user", "apply_rules", 1, steps)
    assert error is None
    assert version["version_number"] == 2 and version["parent_version_id"] == 1
    assert version["row_count"] == 29 and version["column_count"] == 6
    dataset = next(d for d in db["datasets"] if d["id"] == 1)
    assert dataset["current_version_id"] == version["id"]
    assert "thu_dien_tu" in db["frames"][version["id"]].columns
    assert len(db["frames"][1]) == 30  # phiên bản cũ nguyên vẹn để hoàn tác

    listed, _, _ = call_api("user", "list_dataset_versions", 1, state={"_mock_db": db})
    assert [v["version_number"] for v in listed] == [1, 2]


def test_api_apply_validation_and_permissions(call_api):
    _, error, _ = call_api("user", "apply_rules", 1, [])
    assert error.status_code == 422 and "Không có bước nào" in error.detail
    _, error, _ = call_api("user", "apply_rules", 1, [_step("trim_whitespace", "khong_co")])
    assert error.status_code == 422
    _, error, _ = call_api("user", "apply_rules", 999, [_step("drop_duplicates")])
    assert error.status_code == 404


# ---------------------------------------------------------------- trang


def _open(run_view, **extra):
    return run_view("suggestions", role="user", state={**CONTEXT, **extra})


def _generated(run_view):
    at = _open(run_view)
    find_button(at, "Sinh gợi ý").click().run()
    return at


def _accept(at, *ids):
    for suggestion_id in ids:
        at.button(key=f"accept_{suggestion_id}").click().run()
    return at


def _ids(at):
    return [s["id"] for s in at.session_state["_mock_db"]["suggestions"]]


def test_empty_state_offers_generation(run_view):
    at = _open(run_view)
    assert not at.exception
    assert any("Chưa có gợi ý cho phiên bản này" in m.value for m in at.markdown)
    assert any(b.label == "Sinh gợi ý" for b in at.button)
    assert not any(b.label == "Xem trước" for b in at.button)


def test_generate_shows_cards_and_counts(run_view):
    at = _generated(run_view)
    assert not at.exception
    assert {m.label: m.value for m in at.metric} == {
        "Tổng gợi ý": "8",
        "Chưa duyệt": "8",
        "Đã chấp nhận": "0",
        "Đã từ chối": "0",
    }
    assert len([b for b in at.button if b.key and b.key.startswith("accept_")]) == 8
    suggestion_expanders = [e for e in at.expander if e.label == "Xem quy tắc JSON"]
    assert len(suggestion_expanders) == 8  # rule JSON trong từng thẻ
    assert len(at.code) == 9  # 8 quy tắc AI và cấu trúc JSON của tab tự viết
    html = " ".join(m.value for m in at.markdown)
    assert "Độ tin cậy thấp" in html and "AI đề xuất" in html
    assert any("Chọn một bước từ" in i.value for i in at.info)


def test_accept_and_reject_update_status_and_counts(run_view):
    at = _generated(run_view)
    first, second, *_ = _ids(at)
    _accept(at, first)
    at.button(key=f"reject_{second}").click().run()
    assert {m.label: m.value for m in at.metric}["Đã chấp nhận"] == "1"
    assert {m.label: m.value for m in at.metric}["Đã từ chối"] == "1"
    assert at.button(key=f"accept_{first}").disabled  # đã chấp nhận thì khóa nút
    assert any(b.label == "Xem trước" for b in at.button)


def test_status_filter(run_view):
    at = _generated(run_view)
    _accept(at, _ids(at)[0])
    at.radio(key="suggestion_filter").set_value("Đã chấp nhận").run()
    assert len([b for b in at.button if b.key and b.key.startswith("accept_")]) == 1
    at.radio(key="suggestion_filter").set_value("Đã từ chối").run()
    assert any("Không có gợi ý nào ở trạng thái" in i.value for i in at.info)


def test_accept_all_pending(run_view):
    at = _generated(run_view)
    find_button(at, "Chấp nhận tất cả chưa duyệt").click().run()
    assert {m.label: m.value for m in at.metric}["Đã chấp nhận"] == "8"
    assert find_button(at, "Chấp nhận tất cả chưa duyệt").disabled


def test_preview_is_required_before_apply(run_view):
    at = _generated(run_view)
    _accept(at, _ids(at)[0])
    assert at.button(key="apply_changes").disabled
    assert any("Bấm “Xem trước”" in c.value for c in at.caption)

    find_button(at, "Xem trước").click().run()
    assert not at.exception
    assert not at.button(key="apply_changes").disabled
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Dòng bị ảnh hưởng"] == "1" and metrics["Mẫu xem trước"] == "30 dòng"
    labels = [t.label for t in at.tabs]
    assert "Gợi ý AI (8)" in labels
    assert "Quy tắc có sẵn" in labels
    assert "Tự viết quy tắc" in labels
    assert labels[-3:] == ["Thay đổi theo ô", "Dữ liệu sau", "Dữ liệu trước"]


def test_changing_selection_invalidates_preview(run_view):
    at = _generated(run_view)
    first, second, *_ = _ids(at)
    _accept(at, first)
    find_button(at, "Xem trước").click().run()
    _accept(at, second)
    assert at.button(key="apply_changes").disabled
    assert any("Lựa chọn đã thay đổi" in i.value for i in at.info)


def test_adding_queue_step_relocks_apply_until_preview_is_refreshed(run_view):
    at = _generated(run_view)
    _accept(at, _ids(at)[0])
    find_button(at, "Xem trước").click().run()
    assert not at.button(key="apply_changes").disabled

    at.selectbox(key="sys_rule_select").set_value("drop_duplicates").run()
    find_button(at, "+ Thêm vào hàng đợi").click().run()
    assert not at.exception
    assert at.button(key="apply_changes").disabled
    assert any("Lựa chọn đã thay đổi" in i.value for i in at.info)

    find_button(at, "Xem trước").click().run()
    assert not at.button(key="apply_changes").disabled


def test_ai_and_library_steps_share_reorderable_queue(run_view):
    at = _generated(run_view)
    _accept(at, _ids(at)[0])
    at.selectbox(key="sys_rule_select").set_value("drop_duplicates").run()
    find_button(at, "+ Thêm vào hàng đợi").click().run()

    entries = at.session_state["work_context"]["rule_queue"]
    assert [entry["source"] for entry in entries] == ["suggestion", "system"]
    at.button(key="q_down_0").click().run()
    entries = at.session_state["work_context"]["rule_queue"]
    assert [entry["source"] for entry in entries] == ["system", "suggestion"]

    at.button(key="q_del_0").click().run()
    entries = at.session_state["work_context"]["rule_queue"]
    assert len(entries) == 1 and entries[0]["source"] == "suggestion"


def test_apply_after_confirmation_creates_version_and_resets_state(run_view):
    at = _generated(run_view)
    _accept(at, *_ids(at)[:2])  # xóa trùng + cắt khoảng trắng
    find_button(at, "Xem trước").click().run()
    at.session_state["apply_changes__confirmed"] = True  # mô phỏng bấm "Áp dụng" trong hộp thoại
    at.run()
    assert not at.exception
    db = at.session_state["_mock_db"]
    dataset = next(d for d in db["datasets"] if d["id"] == 1)
    assert dataset["current_version_id"] == 2 and len(db["frames"][2]) == 29
    context = at.session_state["work_context"]
    assert context["preview"] is None and context["last_applied"]["version_number"] == 2
    assert any("Đã áp dụng 2 bước" in s.value for s in at.success)
    assert any(b.label == "Xem lịch sử phiên bản" for b in at.button)
    # phiên bản mới chưa có gợi ý: quay về trạng thái rỗng để sinh mới
    assert any(b.label == "Sinh gợi ý" for b in at.button)


def _clean_db(call_api):
    """Áp dụng mọi gợi ý (qua API mock) cho tới khi dữ liệu không còn gợi ý nào."""
    db = None
    for _ in range(5):
        state = {"_mock_db": db} if db else None
        dataset, _, db = call_api("user", "get_dataset", 1, state=state)
        version_id = dataset["current_version_id"]
        found, _, db = call_api("user", "generate_suggestions", version_id, state={"_mock_db": db})
        if not found:
            return db
        steps = [step for item in found for step in item["proposed_rule"]["steps"]]
        _, error, db = call_api("user", "apply_rules", 1, steps, state={"_mock_db": db})
        assert error is None
    raise AssertionError("gợi ý lặp vô hạn")


def test_clean_data_shows_no_issues_state(run_view, call_api):
    db = _clean_db(call_api)
    at = run_view("suggestions", role="user", state={**CONTEXT, "_mock_db": db})
    find_button(at, "Sinh gợi ý").click().run()
    assert not at.exception
    assert any("Dữ liệu đã sạch" in m.value for m in at.markdown)
    assert any(b.label == "Xuất dữ liệu" for b in at.button)
    assert any(b.label == "Phân tích lại" for b in at.button)


def test_mapping_steps_run_last_and_can_be_toggled(run_view):
    rename = {"op": "rename_column", "column": "email", "params": {"new_name": "thu_dien_tu"}}
    context = {"dataset_id": 1, "pending_steps": [rename], "pending_version_id": 1}
    at = run_view("suggestions", role="user", state={"work_context": dict(context)})
    assert any("Đổi tên cột từ bước Mapping" in m.value for m in at.markdown)
    find_button(at, "Sinh gợi ý").click().run()
    _accept(at, _ids(at)[1])  # trim_whitespace(email) chạy TRƯỚC khi đổi tên
    page_text = " ".join([m.value for m in at.markdown] + [c.value for c in at.caption])
    assert "2 bước sẽ được áp dụng" in page_text
    assert "Cắt khoảng trắng thừa" in page_text
    assert "Đổi tên cột “email”" in page_text

    find_button(at, "Xem trước").click().run()
    at.session_state["apply_changes__confirmed"] = True
    at.run()
    frame = at.session_state["_mock_db"]["frames"][2]
    assert "thu_dien_tu" in frame.columns and "email" not in frame.columns
    assert at.session_state["work_context"]["pending_steps"] is None  # đã dùng xong

    # tắt công tắc thì không đưa bước đổi tên vào
    at2 = run_view("suggestions", role="user", state={"work_context": dict(context)})
    at2.toggle(key="include_mapping").set_value(False).run()
    assert not any("sẽ được áp dụng" in m.value for m in at2.markdown)


def test_mapping_steps_for_other_version_are_ignored(run_view):
    rename = {"op": "rename_column", "column": "email", "params": {"new_name": "x"}}
    context = {"dataset_id": 1, "pending_steps": [rename], "pending_version_id": 99}
    at = run_view("suggestions", role="user", state={"work_context": context})
    assert not any("Đổi tên cột từ bước Mapping" in m.value for m in at.markdown)


def test_regenerate_button_exists_after_generation(run_view):
    at = _generated(run_view)
    assert any(b.label == "Sinh lại gợi ý" for b in at.button)


def test_error_states(run_view, monkeypatch):
    def boom(token, version_id, status_out=None):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "list_suggestions", boom)
    at = _open(run_view)
    assert not at.exception
    assert any("chưa sẵn sàng" in e.value for e in at.error)
    assert any(b.label == "Thử lại" for b in at.button)


def test_generate_failure_keeps_page_usable(run_view, monkeypatch):
    at = _open(run_view)

    def boom(token, version_id, status_out=None):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "generate_suggestions", boom)
    find_button(at, "Sinh gợi ý").click().run()
    assert not at.exception
    assert any("chưa sẵn sàng" in e.value for e in at.error)
    assert any(b.label == "Sinh gợi ý" for b in at.button)  # vẫn thử lại được


def test_page_without_dataset(run_view):
    at = run_view("suggestions", role="user")
    assert any("Chưa chọn dataset" in m.value for m in at.markdown)
