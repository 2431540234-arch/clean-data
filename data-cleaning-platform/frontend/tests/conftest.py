"""Fixture dùng chung cho test frontend: chạy từng trang bằng AppTest với backend giả (mock)."""

import copy
import os

# Phải đặt trước khi api_client được import: toàn bộ test chạy với dữ liệu mẫu.
os.environ["FRONTEND_MOCK"] = "1"

from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent

# Khớp dữ liệu seed của mock_api (id 1 = admin, id 2 = user thường).
_ROLES = {
    "admin": ("mock-token-1", {"id": 1, "email": "admin@example.com", "role": "admin"}),
    "user": ("mock-token-2", {"id": 2, "email": "user@example.com", "role": "user"}),
}


@pytest.fixture
def run_view():
    """Trả hàm chạy một trang trong views/; role="user"|"admin" để giả lập đã đăng nhập."""

    def _run(
        name: str,
        *,
        role: str | None = None,
        state: dict[str, Any] | None = None,
        timeout: float = 30,
    ) -> AppTest:
        at = AppTest.from_file(str(FRONTEND_DIR / "views" / f"{name}.py"), default_timeout=timeout)
        if role:
            token, user = _ROLES[role]
            at.session_state["access_token"] = token
            at.session_state["current_user"] = {**user, "full_name": f"Người dùng {role}"}
        for key, value in (state or {}).items():
            # sao chép sâu: trang sửa trực tiếp dict ngữ cảnh nên test không được dùng chung nó
            at.session_state[key] = copy.deepcopy(value)
        return at.run()

    return _run


def error_text(at: AppTest) -> str:
    """Gộp nội dung mọi st.error đang hiển thị."""
    return " ".join(str(e.value) for e in at.error)


def find_input(at: AppTest, label: str, nth: int = 0):
    """Ô st.text_input theo nhãn (nth để phân biệt các ô trùng nhãn giữa hai tab)."""
    return [t for t in at.text_input if t.label == label][nth]


def find_button(at: AppTest, text: str):
    """Nút có nhãn chứa `text`."""
    return next(b for b in at.button if text in b.label)


@pytest.fixture
def call_api():
    """Gọi một hàm của api_client (đang trỏ vào mock) trong ngữ cảnh phiên Streamlit.

    Trả (kết quả, lỗi) và trạng thái mock sau khi gọi, để kiểm tra tác dụng lên dữ liệu.
    """

    def script() -> None:
        import streamlit as st

        import api_client

        name, args, kwargs = st.session_state["_call"]
        func = getattr(api_client, name)
        token = st.session_state["access_token"]
        try:
            st.session_state["_result"] = (func(token, *args, **kwargs), None)
        except api_client.APIError as exc:
            st.session_state["_result"] = (None, exc)

    def _call(
        as_role: str, name: str, *args: Any, state: dict[str, Any] | None = None, **kwargs: Any
    ):
        at = AppTest.from_function(script, default_timeout=30)
        at.session_state["access_token"] = _ROLES[as_role][0]
        at.session_state["_call"] = (name, args, kwargs)
        for key, value in (state or {}).items():
            at.session_state[key] = copy.deepcopy(value)
        at.run()
        assert not at.exception, at.exception
        result, error = at.session_state["_result"]
        return result, error, at.session_state["_mock_db"]

    return _call
