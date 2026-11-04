"""Component giao diện dùng chung: page shell, trạng thái loading/rỗng/lỗi, badge, stepper...

Mọi màn hình dựng từ các hàm ở đây để giữ nhất quán. Không gọi API trực tiếp ở file này.
"""

from collections.abc import Callable
from html import escape
from typing import Any, Literal

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitAPIException

from api_client import APIConnectionError, APIError, data_source_hint, data_source_label
from components.auth_guard import require_admin, require_login
from components.navigation import FLOW_KEYS, get_page, get_page_key
from state import init_state, is_logged_in, logout, pop_flash

BadgeKind = Literal["neutral", "primary", "success", "warning", "error"]

_FLASH_ICONS = {
    "success": ":material/check_circle:",
    "error": ":material/error:",
    "warning": ":material/warning:",
    "info": ":material/info:",
}


# ---------------------------------------------------------------------------
# Khung trang & thông báo
# ---------------------------------------------------------------------------


def show_flash() -> None:
    """Hiển thị thông báo đã đặt bằng state.set_flash (sống sót qua st.rerun)."""
    flash = pop_flash()
    if flash is not None:
        message, kind = flash
        st.toast(message, icon=_FLASH_ICONS.get(kind, _FLASH_ICONS["info"]))


def page_shell(
    title: str | None = None,
    subtitle: str | None = None,
    *,
    page_key: str | None = None,
    admin: bool = False,
    public: bool = False,
) -> None:
    """Mở đầu mọi trang: kiểm tra quyền, hiện thông báo flash, vẽ tiêu đề trang.

    Args:
        title: tiêu đề trang (h1); None để tự vẽ tiêu đề (ví dụ trang đăng nhập).
        subtitle: mô tả ngắn một dòng dưới tiêu đề.
        page_key: key của trang hiện tại để vẽ breadcrumb và active menu header.
        admin: True nếu chỉ admin được xem (lớp bảo vệ thứ hai, ngoài việc ẩn menu).
        public: True nếu trang không cần đăng nhập.
    """
    init_state()
    if admin:
        require_admin()
    elif not public:
        require_login()
    show_flash()
    if not public and is_logged_in():
        from components.header import render_header

        current_page = page_key or get_page_key(title)
        render_header(current_page)
        stepper(current_page)
    if title:
        st.title(title, anchor=False)
    if subtitle:
        st.caption(subtitle)


def data_source_banner(*, show_hint: bool = False) -> None:
    """Banner nhắc đang dùng dữ liệu mẫu (không hiện gì khi dùng backend thật)."""
    label = data_source_label()
    if not label:
        return
    notes = ["Dữ liệu hiển thị không phải dữ liệu thật."]
    hint = data_source_hint() if show_hint else None
    if hint:
        notes.append(hint)
    spans = "".join(f"<span>{escape(note)}</span>" for note in notes)
    st.markdown(
        f'<div class="dc-mock-banner" role="status">{escape(label)}{spans}</div>',
        unsafe_allow_html=True,
    )


def loading(text: str = "Đang tải…"):
    """Context manager hiển thị spinner khi chờ."""
    return st.spinner(text)


def safe_call(label: str, func: Callable[..., Any], *args: Any, **kwargs: Any):
    """Gọi func với spinner, trả về (kết quả, None) hoặc (None, APIError) thay vì raise."""
    with st.spinner(label):
        try:
            return func(*args, **kwargs), None
        except APIError as exc:
            return None, exc


def error_state(exc: APIError, *, key: str = "error_state") -> None:
    """Hiển thị lỗi thân thiện kèm nút Thử lại và chi tiết kỹ thuật (nếu có)."""
    with st.container(border=True):
        if exc.status_code == 401 and is_logged_in():
            st.error(
                "Phiên đăng nhập đã hết hạn hoặc không còn hợp lệ. Vui lòng đăng nhập lại.",
                icon=":material/lock_clock:",
            )
            if st.button("Đăng nhập lại", key=f"{key}_relogin", type="primary"):
                logout()
                st.rerun()
        else:
            icon = (
                ":material/wifi_off:" if isinstance(exc, APIConnectionError) else ":material/error:"
            )
            st.error(exc.detail, icon=icon)
            if st.button("Thử lại", key=f"{key}_retry", icon=":material/refresh:"):
                st.rerun()
        if exc.technical:
            with st.expander("Chi tiết kỹ thuật"):
                st.code(f"HTTP {exc.status_code}\n{exc.technical}", language="text")


def empty_state(
    icon: str,
    title: str,
    description: str,
    *,
    cta_label: str | None = None,
    cta_page: str | None = None,
) -> bool:
    """Trạng thái rỗng: biểu tượng, tiêu đề, mô tả và (tùy chọn) nút dẫn tới bước tiếp theo.

    Args:
        icon: tên Material icon (không kèm dấu hai chấm), ví dụ "inbox".
        cta_page: key trang (components.navigation) mà nút dẫn tới. Bỏ trống thì nút là một
            hành động của trang (ví dụ mở hộp thoại tạo mới) và hàm trả True khi được bấm.
    """
    with st.container(border=True):
        st.markdown(f"**:material/{icon}: {title}**")
        st.caption(description)
        if cta_label:
            clicked = st.button(
                cta_label, key=f"cta_{cta_page or 'action'}_{title}", type="primary"
            )
            if clicked and cta_page:
                st.switch_page(get_page(cta_page).file)
            return clicked and not cta_page
    return False


# ---------------------------------------------------------------------------
# Thành phần hiển thị
# ---------------------------------------------------------------------------


def badge_html(text: str, kind: BadgeKind = "neutral") -> str:
    """HTML của một nhãn trạng thái nhỏ (đã escape), dùng được bên trong HTML khác."""
    return f'<span class="dc-badge dc-badge--{kind}">{escape(text)}</span>'


def badge(text: str, kind: BadgeKind = "neutral") -> None:
    """Hiển thị một nhãn trạng thái nhỏ."""
    st.markdown(badge_html(text, kind), unsafe_allow_html=True)


def section(title: str | None = None, *, caption: str | None = None):
    """Khối nội dung có viền; dùng như `with section("Tiêu đề"): ...`."""
    container = st.container(border=True)
    with container:
        if title:
            st.markdown(f"**{title}**")
        if caption:
            st.caption(caption)
    return container


def metric_card(
    label: str,
    value: str | int | float,
    *,
    help: str | None = None,
    note: str | None = None,
    delta: str | None = None,
    delta_color: str = "off",
) -> None:
    """Thẻ số liệu có viền; `note` là chú thích nhỏ, `delta` là độ chênh so với phiên bản khác."""
    with st.container(border=True):
        st.metric(label, value, delta=delta, delta_color=delta_color, help=help)  # type: ignore[arg-type]
        if note:
            st.caption(note)


def _step_state(current: str | None, key: str) -> str:
    if current not in FLOW_KEYS:
        return "todo"
    current_index = FLOW_KEYS.index(current)
    step_index = FLOW_KEYS.index(key)
    if step_index < current_index:
        return "done"
    return "current" if step_index == current_index else "todo"


def stepper(current: str | None) -> None:
    """Thanh sáu bước có thể bấm, đánh dấu trạng thái theo trang hiện tại."""
    with st.container(key="dc-stepper"):
        columns = st.columns(len(FLOW_KEYS), gap="small")
        for index, (column, key) in enumerate(zip(columns, FLOW_KEYS, strict=True)):
            state = _step_state(current, key)
            if state == "todo":
                icon = ":material/radio_button_unchecked:"
                state_label = "chưa làm"
            elif state == "current":
                icon = ":material/radio_button_checked:"
                state_label = "hiện tại"
            else:
                icon = ":material/check_circle:"
                state_label = "đã xong"
            with column, st.container(key=f"dc-step-item-{index}-{state}"):
                safe_page_link(
                    get_page(key).file,
                    label=f"{index + 1}. {get_page(key).title} · {state_label}",
                    icon=icon,
                    use_container_width=True,
                )


def data_table(
    df: pd.DataFrame,
    *,
    column_config: dict[str, Any] | None = None,
    height: int | None = None,
    key: str | None = None,
) -> None:
    """Bảng dữ liệu chuẩn: full width, ẩn chỉ số dòng."""
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        height=height,
        key=key,
    )


def confirm_button(
    label: str,
    *,
    key: str,
    title: str,
    message: str,
    confirm_label: str = "Xác nhận",
    icon: str | None = None,
    type: Literal["primary", "secondary"] = "secondary",
    disabled: bool = False,
    warning: bool = False,
) -> bool:
    """Nút mở hộp thoại xác nhận. Trả True đúng một lần chạy sau khi người dùng bấm Xác nhận.

    Dùng cho hành động khó hoàn tác (áp dụng rule, khóa user, xóa project...).
    """
    confirmed_key = f"{key}__confirmed"
    if st.button(label, key=key, icon=icon, type=type, disabled=disabled):
        _open_confirm_dialog(key, title, message, confirm_label, warning)
    return bool(st.session_state.pop(confirmed_key, False))


def _open_confirm_dialog(key: str, title: str, message: str, confirm_label: str, warning: bool):
    @st.dialog(title)
    def dialog() -> None:
        (st.warning if warning else st.write)(message)
        cancel_col, confirm_col = st.columns(2)
        if cancel_col.button("Hủy", key=f"{key}__cancel", use_container_width=True):
            st.rerun()
        if confirm_col.button(
            confirm_label, key=f"{key}__ok", type="primary", use_container_width=True
        ):
            st.session_state[f"{key}__confirmed"] = True
            st.rerun()

    dialog()


def safe_page_link(page_file: str, label: str, icon: str | None = None, **kwargs: Any) -> None:
    """Wrapper an toàn cho st.page_link để không bị lỗi StreamlitPageNotFoundError trong AppTest."""
    try:
        st.page_link(page_file, label=label, icon=icon, **kwargs)
    except StreamlitAPIException:
        try:
            rel = page_file.split("/")[-1]
            st.page_link(rel, label=label, icon=icon, **kwargs)
        except StreamlitAPIException:
            if st.button(label, icon=icon, **kwargs):
                st.switch_page(page_file)
