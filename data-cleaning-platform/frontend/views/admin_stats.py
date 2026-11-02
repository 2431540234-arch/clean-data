"""Trang Thống kê hệ thống: chỉ admin. Số user, dataset, lượt gọi AI, điểm chất lượng TB."""

import streamlit as st

from api_client import admin_stats
from components.charts import render_donut_chart
from components.formatting import format_number
from components.quality_gauge import render_quality_gauge, score_label
from components.ui import badge_html, error_state, metric_card, page_shell, safe_call, section
from state import get_token

_ACTIVE, _LOCKED, _ADMIN, _USER = "#16A34A", "#DC2626", "#2563EB", "#94A3B8"

page_shell("Thống kê hệ thống", "Số liệu tổng quan toàn hệ thống", admin=True)

if st.button("Làm mới", icon=":material/refresh:"):
    st.rerun()

stats, error = safe_call("Đang tải thống kê…", admin_stats, get_token())
if error is not None:
    error_state(error, key="admin_stats")
    st.stop()

tiles = [
    ("Người dùng", format_number(stats["total_users"])),
    ("Quản trị viên", format_number(stats["total_admins"])),
    ("Đang hoạt động", format_number(stats["active_users"])),
    ("Project", format_number(stats["total_projects"])),
    ("Dataset", format_number(stats["total_datasets"])),
    ("Lượt gọi AI", format_number(stats["total_ai_calls"])),
]
for start in range(0, len(tiles), 3):
    for cell, (label, value) in zip(st.columns(3), tiles[start : start + 3], strict=True):
        with cell:
            metric_card(label, value)

locked = stats["total_users"] - stats["active_users"]
users_col, roles_col, quality_col = st.columns(3)
with users_col, section("Trạng thái tài khoản"):
    render_donut_chart(
        [("Hoạt động", stats["active_users"]), ("Đã khóa", locked)], [_ACTIVE, _LOCKED]
    )
with roles_col, section("Quyền"):
    render_donut_chart(
        [
            ("Quản trị viên", stats["total_admins"]),
            ("Người dùng", stats["total_users"] - stats["total_admins"]),
        ],
        [_ADMIN, _USER],
    )
with quality_col, section("Điểm chất lượng trung bình"):
    score = stats["average_quality_score"]
    render_quality_gauge(score)
    label, kind = score_label(score)
    value = f"{score:.1f}".replace(".", ",")
    st.markdown(f"**{value} / 100** {badge_html(label, kind)}", unsafe_allow_html=True)
