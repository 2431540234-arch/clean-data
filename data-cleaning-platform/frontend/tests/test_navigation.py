"""Điều hướng theo quyền và việc mọi trang render được (user thường và admin)."""

import pytest
from conftest import error_text

from components.navigation import FLOW_KEYS, PAGES, build_pages

VIEWS = [p.key for p in PAGES if p.key != "login"]
ADMIN_VIEWS = [p.key for p in PAGES if p.admin_only]


def test_logged_out_routes_are_registered_with_login_as_default(monkeypatch):
    monkeypatch.setattr(
        "components.navigation.st.Page",
        lambda path, **kwargs: (path, kwargs),
    )
    pages = build_pages(False, False)

    assert len(pages) == len(PAGES)
    assert pages[0][0] == "views/login.py"
    assert pages[0][1]["default"] is True
    assert all(not options["default"] for _, options in pages[1:])


def test_logged_out_direct_route_redirects_to_login(run_view, monkeypatch):
    redirected = []
    monkeypatch.setattr("streamlit.switch_page", lambda page: redirected.append(page))

    at = run_view("account")

    assert redirected == ["views/login.py"]
    assert at.session_state["flash_message"] == (
        "Vui lòng đăng nhập để tiếp tục.",
        "warning",
    )


def test_admin_group_only_for_admin():
    assert "Quản trị" in build_pages(True, True)
    assert "Quản trị" not in build_pages(True, False)


def test_flow_follows_backend_dependency_order():
    assert FLOW_KEYS == ("upload", "overview", "mapping", "suggestions", "history", "export")


@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize("role", ["user", "admin"])
def test_view_renders(run_view, view, role):
    at = run_view(view, role=role)
    if view in ADMIN_VIEWS and role == "user":
        assert "không có quyền" in error_text(at)
    else:
        assert not at.exception
        assert len(at.title) == 1
