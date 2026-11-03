"""Nhóm 4 - POST /mapping/{version_id}/suggest."""

from tests.conftest import FIXTURES_DIR

DEMO_CSV = FIXTURES_DIR.parent.parent.parent / "sample_data" / "khach_hang_tieu_de_khac.csv"
TARGET = ["ho_ten", "email", "so_dien_thoai", "ngay_sinh", "tuoi", "tinh_thanh"]


def _version(client, headers, path=DEMO_CSV):
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()["id"]
    response = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": (path.name, path.read_bytes())},
        headers=headers,
    )
    return response.json()["first_version"]["id"]


def _suggest(client, headers, version_id, body):
    return client.post(f"/api/v1/mapping/{version_id}/suggest", json=body, headers=headers)


def test_suggest_maps_every_source_column_in_order(client, user_headers):
    version_id = _version(client, user_headers)
    response = _suggest(client, user_headers, version_id, TARGET)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "Họ và tên": "ho_ten",
        "Email liên hệ": "email",
        "Số ĐT": "so_dien_thoai",
        "Ngày sinh": "ngay_sinh",
        "Tuổi": "tuoi",
        "Tỉnh/Thành phố": "tinh_thanh",
        "Ghi chú": None,
    }
    assert list(response.json()) == [
        "Họ và tên",
        "Email liên hệ",
        "Số ĐT",
        "Ngày sinh",
        "Tuổi",
        "Tỉnh/Thành phố",
        "Ghi chú",
    ]


def test_suggest_with_empty_schema_returns_all_null(client, user_headers):
    version_id = _version(client, user_headers)
    response = _suggest(client, user_headers, version_id, [])
    assert response.status_code == 200
    assert set(response.json().values()) == {None} and len(response.json()) == 7


def test_suggest_rejects_bad_bodies(client, user_headers):
    version_id = _version(client, user_headers)
    assert (
        _suggest(client, user_headers, version_id, {"a": 1}).status_code == 422
    )  # không phải mảng
    assert _suggest(client, user_headers, version_id, [1, 2]).status_code == 422
    assert _suggest(client, user_headers, version_id, ["ok", "  "]).status_code == 422
    assert _suggest(client, user_headers, version_id, ["x" * 300]).status_code == 422
    assert (
        _suggest(client, user_headers, version_id, [f"c{i}" for i in range(501)]).status_code == 422
    )


def test_suggest_permissions(client, user_headers, other_headers, admin_headers):
    version_id = _version(client, user_headers)
    url = f"/api/v1/mapping/{version_id}/suggest"
    assert client.post(url, json=TARGET).status_code == 401
    assert _suggest(client, other_headers, version_id, TARGET).status_code == 403
    assert _suggest(client, user_headers, 999999, TARGET).status_code == 404
    assert _suggest(client, admin_headers, version_id, TARGET).status_code == 200
