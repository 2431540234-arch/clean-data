"""Nhóm 7 - điểm chất lượng, xuất CSV/Excel, xem dòng theo trang, điểm trung bình của project."""

import io

from openpyxl import load_workbook
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.export import Export
from app.models.quality_report import QualityReport
from tests.conftest import FIXTURES_DIR

DIRTY = (FIXTURES_DIR / "dirty_sample.csv").read_bytes()


def _upload(client, headers, content=DIRTY, name="dirty_sample.csv", project_id=None):
    if project_id is None:
        project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()[
            "id"
        ]
    body = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": (name, content)},
        headers=headers,
    ).json()
    return body["dataset"]["id"], body["first_version"]["id"], project_id


# ---------------------------------------------------------------- quality


def test_quality_report_shape_ranges_and_caching(client, db, user_headers):
    _, version_id, _ = _upload(client, user_headers)
    response = client.get(f"/api/v1/quality/{version_id}", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version_id"] == version_id and 0 < body["overall_score"] < 100
    for key in ("completeness", "uniqueness", "validity", "consistency"):
        assert 0 <= body[key] <= 1
    assert body["issue_summary"]["duplicate_rows"] == 1
    assert body["issue_summary"]["rows"] == 30
    again = client.get(f"/api/v1/quality/{version_id}", headers=user_headers).json()
    assert again == body  # lần hai đọc lại bản đã lưu
    assert db.scalar(select(func.count()).select_from(QualityReport)) == 1


def test_profiling_run_also_stores_quality_so_it_is_free_later(client, db, user_headers):
    _, version_id, _ = _upload(client, user_headers)
    client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    assert db.scalar(select(func.count()).select_from(QualityReport)) == 1
    assert client.get(f"/api/v1/quality/{version_id}", headers=user_headers).status_code == 200


def test_quality_computed_for_already_profiled_version_without_report(client, db, user_headers):
    _, version_id, _ = _upload(client, user_headers)
    client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    db.query(QualityReport).delete()
    db.commit()
    response = client.get(f"/api/v1/quality/{version_id}", headers=user_headers)
    assert response.status_code == 200
    assert db.scalar(select(func.count()).select_from(QualityReport)) == 1


def test_cleaning_improves_quality_score(client, user_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    before = client.get(f"/api/v1/quality/{v1}", headers=user_headers).json()["overall_score"]
    suggestions = client.post(
        "/api/v1/suggestions/generate", json={"version_id": v1}, headers=user_headers
    ).json()
    steps = [
        step
        for s in suggestions
        if not s["proposed_rule"]["steps"][0]["params"].get("drop_invalid")
        for step in s["proposed_rule"]["steps"]
    ]
    v2 = client.post(
        f"/api/v1/versions/{dataset_id}/apply", json={"steps": steps}, headers=user_headers
    ).json()["id"]
    after = client.get(f"/api/v1/quality/{v2}", headers=user_headers).json()["overall_score"]
    assert after > before


def test_quality_permissions(client, user_headers, other_headers, admin_headers):
    _, version_id, _ = _upload(client, user_headers)
    url = f"/api/v1/quality/{version_id}"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=other_headers).status_code == 403
    assert client.get("/api/v1/quality/999999", headers=user_headers).status_code == 404
    assert client.get(url, headers=admin_headers).status_code == 200


# ---------------------------------------------------------------- export


def test_export_csv_download(client, db, user_headers, normal_user):
    _, version_id, _ = _upload(client, user_headers, name="Khách hàng.csv")
    response = client.get(f"/api/v1/export/{version_id}/csv", headers=user_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;") and "filename*=UTF-8''" in disposition
    assert "Kh%C3%A1ch_h%C3%A0ng_v1.csv" in disposition
    assert response.content.startswith(b"\xef\xbb\xbf")
    text = response.content.decode("utf-8-sig")
    assert text.splitlines()[0] == "ho_ten,email,so_dien_thoai,ngay_sinh,tuoi,tinh_thanh"
    assert len(text.splitlines()) == 31
    record = db.scalars(select(Export)).one()
    assert (record.format, record.exported_by, record.file_size) == (
        "csv",
        normal_user.id,
        len(response.content),
    )
    log = db.scalars(select(AuditLog).where(AuditLog.action == "dataset.export")).one()
    assert log.new_value["format"] == "csv"


def test_export_csv_neutralizes_formulas(client, user_headers):
    content = 'ten,ghi_chu\nAn,=HYPERLINK("http://x")\nBình,bình thường\n'.encode()
    _, version_id, _ = _upload(client, user_headers, content, "f.csv")
    text = client.get(f"/api/v1/export/{version_id}/csv", headers=user_headers).content.decode(
        "utf-8-sig"
    )
    assert "'=HYPERLINK" in text and ",=HYPERLINK" not in text


def test_export_excel_has_data_report_and_issue_sheets(client, db, user_headers):
    _, version_id, _ = _upload(client, user_headers)
    response = client.get(f"/api/v1/export/{version_id}/excel", headers=user_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Dữ liệu", "Báo cáo chất lượng", "Lỗi đã phát hiện"]
    assert workbook["Dữ liệu"].max_row == 31
    report = {
        row[0].value: row[1].value for row in workbook["Báo cáo chất lượng"].iter_rows(min_row=2)
    }
    assert 0 < report["Điểm chất lượng (0-100)"] < 100 and report["Số dòng"] == 30
    assert workbook["Lỗi đã phát hiện"].max_row > 2
    export = db.scalars(select(Export)).one()
    assert export.format == "xlsx" and export.include_quality_report is True


def test_export_excel_keeps_formula_text_as_text(client, user_headers):
    content = b"ten,ghi_chu\nAn,=1+1\n"
    _, version_id, _ = _upload(client, user_headers, content, "f.csv")
    response = client.get(f"/api/v1/export/{version_id}/excel", headers=user_headers)
    cell = load_workbook(io.BytesIO(response.content))["Dữ liệu"]["B2"]
    assert cell.value == "=1+1" and cell.data_type == "s"


def test_export_permissions(client, db, user_headers, other_headers):
    _, version_id, _ = _upload(client, user_headers)
    for kind in ("csv", "excel"):
        url = f"/api/v1/export/{version_id}/{kind}"
        assert client.get(url).status_code == 401
        assert client.get(url, headers=other_headers).status_code == 403
        assert (
            client.get(url.replace(str(version_id), "999999"), headers=user_headers).status_code
            == 404
        )
    assert db.scalar(select(func.count()).select_from(Export)) == 0  # bị từ chối: không ghi lịch sử


# ---------------------------------------------------------------- xem dòng theo trang


def test_rows_pagination(client, user_headers):
    dataset_id, version_id, _ = _upload(client, user_headers)
    base = f"/api/v1/datasets/{dataset_id}/versions/{version_id}/rows"
    first = client.get(f"{base}?offset=0&limit=10", headers=user_headers).json()
    assert first["total"] == 30 and first["offset"] == 0 and first["limit"] == 10
    assert first["columns"] == [
        "ho_ten",
        "email",
        "so_dien_thoai",
        "ngay_sinh",
        "tuoi",
        "tinh_thanh",
    ]
    assert [r["row_index"] for r in first["rows"]] == list(range(10))
    assert first["rows"][0]["values"]["ho_ten"] == "Nguyen Van An"
    last = client.get(f"{base}?offset=25&limit=10", headers=user_headers).json()
    assert [r["row_index"] for r in last["rows"]] == [25, 26, 27, 28, 29]
    beyond = client.get(f"{base}?offset=100", headers=user_headers).json()
    assert beyond["rows"] == [] and beyond["total"] == 30
    default = client.get(base, headers=user_headers).json()
    assert default["limit"] == 100 and len(default["rows"]) == 30
    empty_cell = next(r for r in default["rows"] if r["values"]["email"] is None)  # ô trống -> null
    assert empty_cell["values"]["email"] is None


def test_rows_validation_and_permissions(client, user_headers, other_headers):
    dataset_id, version_id, _ = _upload(client, user_headers)
    other_dataset, other_version, _ = _upload(client, user_headers)
    base = f"/api/v1/datasets/{dataset_id}/versions/{version_id}/rows"
    for query in ("offset=-1", "limit=0", "limit=1001", "offset=abc"):
        assert client.get(f"{base}?{query}", headers=user_headers).status_code == 422
    assert client.get(base).status_code == 401
    assert client.get(base, headers=other_headers).status_code == 403
    assert (
        client.get(
            f"/api/v1/datasets/{dataset_id}/versions/999999/rows", headers=user_headers
        ).status_code
        == 404
    )
    mismatch = f"/api/v1/datasets/{dataset_id}/versions/{other_version}/rows"
    assert client.get(mismatch, headers=user_headers).status_code == 404
    assert (
        client.get(
            f"/api/v1/datasets/999999/versions/{version_id}/rows", headers=user_headers
        ).status_code
        == 404
    )


# ---------------------------------------------------------------- điểm trung bình project


def test_project_average_quality_only_when_reports_exist(client, user_headers):
    dataset_id, v1, project_id = _upload(client, user_headers)
    listed = client.get("/api/v1/projects", headers=user_headers).json()
    assert listed[0]["average_quality_score"] is None and listed[0]["dataset_count"] == 1
    score_1 = client.get(f"/api/v1/quality/{v1}", headers=user_headers).json()["overall_score"]
    assert (
        client.get("/api/v1/projects", headers=user_headers).json()[0]["average_quality_score"]
        == score_1
    )
    clean = b"ten,tuoi\nAn,29\nBinh,34\nCuong,37\n"
    _, v2, _ = _upload(client, user_headers, clean, "s.csv", project_id=project_id)
    score_2 = client.get(f"/api/v1/quality/{v2}", headers=user_headers).json()["overall_score"]
    average = client.get("/api/v1/projects", headers=user_headers).json()[0][
        "average_quality_score"
    ]
    assert average == round((score_1 + score_2) / 2, 1)


def test_project_average_uses_current_version(client, user_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    client.get(f"/api/v1/quality/{v1}", headers=user_headers)
    v2 = client.post(
        f"/api/v1/versions/{dataset_id}/apply",
        json={"steps": [{"op": "drop_duplicates", "params": {}}]},
        headers=user_headers,
    ).json()["id"]
    # v2 chưa có báo cáo: project không có điểm cho phiên bản hiện tại
    assert (
        client.get("/api/v1/projects", headers=user_headers).json()[0]["average_quality_score"]
        is None
    )
    score_2 = client.get(f"/api/v1/quality/{v2}", headers=user_headers).json()["overall_score"]
    assert (
        client.get("/api/v1/projects", headers=user_headers).json()[0]["average_quality_score"]
        == score_2
    )
