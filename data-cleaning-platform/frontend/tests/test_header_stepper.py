"""Header chung, quyền hiển thị menu và trạng thái stepper."""

from pathlib import Path

from components.navigation import FLOW_KEYS
from components.ui import _step_state


def test_header_nav_only_scrolls_at_mobile_breakpoint():
    css_path = Path(__file__).resolve().parents[1] / "assets" / "styles.css"
    css = css_path.read_text(encoding="utf-8")

    assert ".st-key-dc-header-nav {\n    max-width: 100%;\n    overflow-x: hidden;" in css
    assert "flex: 1 1 0 !important;" in css
    mobile_styles = css.split("@media (max-width: 768px) {", maxsplit=1)[1]
    assert ".st-key-dc-header-nav {" in mobile_styles
    assert "overflow-x: auto;" in mobile_styles


def test_stepper_marks_cleaning_as_current_step_four():
    assert [_step_state("suggestions", key) for key in FLOW_KEYS] == [
        "done",
        "done",
        "done",
        "current",
        "todo",
        "todo",
    ]


def test_stepper_has_no_current_step_outside_cleaning_flow():
    assert {_step_state("home", key) for key in FLOW_KEYS} == {"todo"}


def _step_links(at):
    """Nhãn các bước trong thanh bước (AppTest dựng liên kết trang thành nút hoặc page_link)."""
    labels = [b.label for b in at.button] + [link.proto.label for link in at.get("page_link")]
    return [
        label
        for label in labels
        if label[:1].isdigit() and any(s in label for s in ("chưa làm", "hiện tại", "đã xong"))
    ]


def test_stepper_only_appears_on_the_six_flow_pages(run_view):
    for key in ("home", "audit", "account", "rule_library", "dashboard"):
        assert not _step_links(run_view(key, role="user")), key
    at = run_view("upload", role="user")
    assert len(_step_links(at)) == len(FLOW_KEYS)
    assert any("hiện tại" in label and "Tải lên" in label for label in _step_links(at))


def test_header_admin_menu_is_only_visible_to_admin(run_view):
    user_page = run_view("home", role="user")
    admin_page = run_view("home", role="admin")

    assert not user_page.exception and not admin_page.exception
    assert not any("Quản trị" in button.label for button in user_page.button)
    assert any("Quản trị" in button.label for button in admin_page.button)


def test_header_project_switch_clears_project_scoped_context(run_view):
    page = run_view(
        "dashboard",
        role="user",
        state={
            "work_context": {
                "project_id": 1,
                "project_name": "Khách hàng 2026",
                "dataset_id": 1,
                "dataset_name": "khach_hang_ban.csv",
                "version_id": 1,
                "rule_queue": [{"op": "drop_duplicates", "params": {}}],
                "preview": {"signature": "old"},
                "pending_steps": [
                    {"op": "rename_column", "column": "a", "params": {"new_name": "b"}}
                ],
                "pending_version_id": 1,
            }
        },
    )

    page.selectbox(key="header_quick_project_select").set_value(2).run()

    context = page.session_state["work_context"]
    assert context["project_id"] == 2
    assert context["dataset_id"] is None
    assert context["rule_queue"] == [] and context["preview"] is None
    assert context["rule_queue_version_id"] is None
    assert context["pending_steps"] is None and context["pending_version_id"] is None


def test_header_default_project_matches_work_context(run_view):
    page = run_view("home", role="user")
    context = page.session_state["work_context"]
    assert context["project_id"] == 1
    assert context["project_name"] == "Khách hàng 2026"
