"""Header ứng dụng 2 hàng chuẩn theo Wireframe Khung 15.

Hàng 1: Logo DC DataClean, Breadcrumb vị trí trang, Selectbox chọn dự án nhanh,
        Pill thông tin người dùng (avatar, tên, vai trò) và nút Đăng xuất.
Hàng 2: Menu ngang các trang (Trang chủ, Dự án, Làm sạch dữ liệu, Thư viện quy tắc,
        Nhật ký, Tài khoản, Quản trị), đánh dấu trang đang mở.
Hỗ trợ responsive 375px: cuộn ngang hoặc flex-wrap gọn gàng, không xếp chồng thành cột dọc.
"""

from html import escape

import streamlit as st

from api_client import APIError, list_projects
from components.navigation import FLOW_KEYS, HEADER_NAV_KEYS, get_page
from components.ui import badge_html, safe_page_link
from components.work_context import project_context
from state import (
    get_context,
    get_current_user,
    get_token,
    is_admin,
    is_logged_in,
    logout,
    set_context,
    set_flash,
)


def _change_project(project_names: dict[int, str]) -> None:
    selected_project_id = st.session_state["header_quick_project_select"]
    context = get_context()
    if selected_project_id == context.get("project_id"):
        return
    set_context(
        **project_context({"id": selected_project_id, "name": project_names[selected_project_id]})
    )


def render_header(current_page_key: str = "home") -> None:
    """Vẽ Header 2 hàng ở đầu trang."""
    if not is_logged_in():
        return

    user = get_current_user() or {}
    name = str(user.get("full_name") or user.get("email") or "Người dùng")
    initials = "".join([part[0] for part in name.split() if part])[:2].upper() or "DC"
    role_label = "Quản trị viên" if is_admin() else "Người dùng"
    role_kind = "primary" if is_admin() else "neutral"

    # Lấy thông tin trang hiện tại để làm breadcrumb
    page_def = get_page(current_page_key)
    page_title = page_def.title
    area_name = page_def.group or "Chung"

    # --- HÀNG 1: TOP BAR ---
    with st.container(key="dc-header-top"):
        top_col_brand, top_col_project, top_col_user, top_col_logout = st.columns(
            [4.4, 2.6, 3.0, 2.0], gap="small", vertical_alignment="center"
        )

        with top_col_brand:
            st.markdown(
                f"""<div class="dc-header-brand">
                <span class="dc-logo-badge">DC</span>
                <span class="dc-logo-text">DataClean</span>
                <span class="dc-breadcrumb-sep">·</span>
                <span class="dc-breadcrumb-area">{escape(area_name)}</span>
                <span class="dc-breadcrumb-sep">/</span>
                <span class="dc-breadcrumb-title">{escape(page_title)}</span>
            </div>""",
                unsafe_allow_html=True,
            )

        with top_col_project:
            projects: list[dict] = []
            token = get_token()
            if token:
                try:
                    projects = list_projects(token)
                except APIError as exc:
                    st.error(f"Không tải được danh sách dự án: {exc.detail}")

            context = get_context()
            active_project_id = context.get("project_id")

            if projects:
                options = {p["id"]: p["name"] for p in projects}
                project_ids = list(options)
                if active_project_id not in options and not context.get("dataset_id"):
                    active_project_id = project_ids[0]
                    set_context(
                        **project_context(
                            {"id": active_project_id, "name": options[active_project_id]}
                        )
                    )
                current_index = (
                    project_ids.index(active_project_id) if active_project_id in options else 0
                )
                if (
                    active_project_id in options
                    and st.session_state.get("header_quick_project_select") != active_project_id
                ):
                    st.session_state["header_quick_project_select"] = active_project_id
                st.selectbox(
                    "Dự án",
                    options=project_ids,
                    index=current_index,
                    format_func=lambda pid: options.get(pid, str(pid)),
                    label_visibility="collapsed",
                    key="header_quick_project_select",
                    on_change=_change_project,
                    args=(options,),
                )
            else:
                st.caption("Chưa có dự án")

        with top_col_user:
            badge_code = badge_html(role_label, role_kind)
            st.markdown(
                f"""<div class="dc-header-user-pill">
                <div class="dc-user-avatar">{escape(initials)}</div>
                <div class="dc-user-meta">
                    <span class="dc-user-name" title="{escape(name)}">{escape(name)}</span>
                    {badge_code}
                </div>
            </div>""",
                unsafe_allow_html=True,
            )

        with top_col_logout:
            if st.button(
                "Đăng xuất",
                key="header_logout_btn",
                icon=":material/logout:",
                help="Đăng xuất khỏi hệ thống",
            ):
                logout()
                set_flash("Bạn đã đăng xuất thành công.", "info")
                st.rerun()

    # --- HÀNG 2: MENU NGANG ĐIỀU HƯỚNG ---
    nav_keys = list(HEADER_NAV_KEYS)
    if is_admin():
        nav_keys.append("admin_users")

    if current_page_key in FLOW_KEYS:
        active_nav_key = "suggestions"
    elif current_page_key in ("admin_users", "admin_stats"):
        active_nav_key = "admin_users"
    else:
        active_nav_key = current_page_key

    if current_page_key in ("admin_users", "admin_stats"):
        active_nav_key = "admin_users"

    with st.container(key="dc-header-nav"):
        nav_cols = st.columns(len(nav_keys), gap="small")
        for col, key in zip(nav_cols, nav_keys, strict=True):
            page = get_page(key)
            nav_label = {
                "audit": "Nhật ký",
                "admin_users": "Quản trị",
            }.get(key, page.title)
            with col:
                container_key = (
                    f"dc-nav-item-{key}-active" if key == active_nav_key else f"dc-nav-item-{key}"
                )
                with st.container(key=container_key):
                    safe_page_link(
                        page.file,
                        label=nav_label,
                        icon=f":material/{page.icon}:",
                        use_container_width=True,
                        help=f"Mở trang {nav_label}",
                    )

    st.markdown('<div class="dc-header-divider"></div>', unsafe_allow_html=True)
