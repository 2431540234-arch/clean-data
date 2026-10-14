"""TODO: test user A không xem/sửa được project, dataset của user B (trừ admin)."""

import pytest


@pytest.mark.skip(reason="TODO: tạo 2 user, user B tạo project, user A gọi API phải bị 403.")
def test_user_cannot_access_other_users_project() -> None:
    pass
