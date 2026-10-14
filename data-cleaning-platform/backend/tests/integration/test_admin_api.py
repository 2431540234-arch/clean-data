"""TODO: test user thường gọi API admin phải bị từ chối với mã 403."""

import pytest


@pytest.mark.skip(reason="TODO: đăng nhập bằng user thường, gọi /api/v1/admin/users, assert 403.")
def test_normal_user_cannot_access_admin_api() -> None:
    pass
