"""Excel chỉ chứa được 1.048.575 dòng dữ liệu mỗi sheet: vượt thì từ chối, không tự cắt dữ liệu."""

import io

import pandas as pd
import pytest
from sqlalchemy import select

from app.api.v1 import export as export_api
from app.core.exceptions import ValidationAppError
from app.models.audit_log import AuditLog
from app.models.export import Export
from app.services import export as export_service
from tests.conftest import FIXTURES_DIR

DIRTY = (FIXTURES_DIR / "dirty_sample.csv").read_bytes()  # 30 dòng dữ liệu


def _version(client, headers):
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()["id"]
    body = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": ("dirty_sample.csv", DIRTY)},
        headers=headers,
    ).json()
    return body["first_version"]["id"]


def test_real_limit_is_one_sheet_minus_the_header_row():
    assert export_service.EXCEL_MAX_DATA_ROWS == 1_048_576 - 1
    export_service.ensure_fits_excel("Dữ liệu", 1_048_575)  # đúng mức trần thì vẫn được
    with pytest.raises(ValidationAppError) as error:
        export_service.ensure_fits_excel("Dữ liệu", 1_048_576)
    message = str(error.value)
    assert "1.048.576" in message and "1.048.575" in message  # số dòng viết kiểu Việt Nam
    assert "Dữ liệu" in message and "CSV" in message


def test_excel_export_is_refused_over_the_limit_but_csv_still_works(
    client, db, user_headers, monkeypatch
):
    version_id = _version(client, user_headers)
    monkeypatch.setattr(export_service, "EXCEL_MAX_DATA_ROWS", 29)  # file có 30 dòng
    response = client.get(f"/api/v1/export/{version_id}/excel", headers=user_headers)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Dữ liệu" in detail and "30 dòng" in detail and "29 dòng" in detail and "CSV" in detail
    # từ chối thì không ghi lịch sử xuất và không có file nào được tạo
    assert db.scalars(select(Export)).all() == []
    assert db.scalars(select(AuditLog).where(AuditLog.action == "dataset.export")).all() == []
    csv = client.get(f"/api/v1/export/{version_id}/csv", headers=user_headers)
    assert csv.status_code == 200
    frame = pd.read_csv(io.BytesIO(csv.content), encoding="utf-8-sig", dtype=str)
    assert len(frame) == 30  # CSV vẫn đủ 30 dòng, không bị cắt


def test_excel_export_at_exactly_the_limit_is_allowed(client, user_headers, monkeypatch):
    version_id = _version(client, user_headers)
    monkeypatch.setattr(export_service, "EXCEL_MAX_DATA_ROWS", 30)
    assert client.get(f"/api/v1/export/{version_id}/excel", headers=user_headers).status_code == 200


def test_the_row_limit_is_checked_before_loading_the_whole_table(client, user_headers, monkeypatch):
    version_id = _version(client, user_headers)
    monkeypatch.setattr(export_service, "EXCEL_MAX_DATA_ROWS", 5)

    def must_not_load(*args, **kwargs):
        raise AssertionError("không được nạp cả bảng khi đã biết vượt giới hạn")

    monkeypatch.setattr(export_api, "load_version_frame", must_not_load)
    response = client.get(f"/api/v1/export/{version_id}/excel", headers=user_headers)
    assert response.status_code == 422


def test_every_sheet_is_checked_including_the_issue_list(monkeypatch):
    monkeypatch.setattr(export_service, "EXCEL_MAX_DATA_ROWS", 3)
    fits = pd.DataFrame({"a": ["1", "2", "3"]})
    too_long = pd.DataFrame({"Cột": list("abcd")})
    export_service.export_to_excel_bytes({"Dữ liệu": fits})  # vừa đủ: xuất được
    with pytest.raises(ValidationAppError, match="Lỗi đã phát hiện") as error:
        export_service.export_to_excel_bytes({"Dữ liệu": fits, "Lỗi đã phát hiện": too_long})
    assert "4 dòng" in str(error.value) and "CSV" in str(error.value)
