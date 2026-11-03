"""Nhóm 6 - preview, áp dụng rule, undo/redo/restore, rule template."""

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.cleaning_operation import CleaningOperation
from app.models.dataset import DatasetVersion
from app.services import storage
from tests.conftest import FIXTURES_DIR

DIRTY = (FIXTURES_DIR / "dirty_sample.csv").read_bytes()
TRIM = {"steps": [{"op": "trim_whitespace", "column": "email", "params": {}}]}
LOWER = {
    "steps": [
        {"op": "standardize_email", "column": "email", "params": {"drop_invalid": False}},
    ]
}
DATES = {
    "steps": [
        {
            "op": "standardize_date",
            "column": "ngay_sinh",
            "params": {"output_format": "%Y-%m-%d", "dayfirst": True},
        }
    ]
}


def _upload(client, headers, content=DIRTY, name="dirty_sample.csv"):
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()["id"]
    body = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": (name, content)},
        headers=headers,
    ).json()
    return body["dataset"]["id"], body["first_version"]["id"], project_id


def _apply(client, headers, dataset_id, rule_set):
    return client.post(f"/api/v1/versions/{dataset_id}/apply", json=rule_set, headers=headers)


def _current(client, headers, dataset_id):
    return client.get(f"/api/v1/datasets/{dataset_id}", headers=headers).json()[
        "current_version_id"
    ]


# ---------------------------------------------------------------- preview


def test_preview_returns_diffs_without_changing_anything(client, db, user_headers):
    dataset_id, version_id, _ = _upload(client, user_headers)
    response = client.post(
        "/api/v1/preview",
        json={"version_id": version_id, "rule_set": LOWER, "sample_rows": 5},
        headers=user_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version_id"] == version_id
    assert len(body["before_rows"]) == len(body["after_rows"]) == 5
    assert all(isinstance(v, str) for row in body["before_rows"] for v in row.values())
    diff = next(d for d in body["diffs"] if d["row_index"] == 1)
    assert diff["column"] == "email"
    assert diff["before"] == " TranThiBinh@GMAIL.com " and diff["after"] == "tranthibinh@gmail.com"
    assert body["affected_row_count"] >= 1
    assert _current(client, user_headers, dataset_id) == version_id
    assert db.scalar(select(DatasetVersion.id).where(DatasetVersion.version_number == 2)) is None


def test_preview_deleted_rows_vanish_from_after_rows_and_diffs_use_before_positions(
    client, user_headers
):
    _, version_id, _ = _upload(client, user_headers)
    rule = {"steps": [{"op": "drop_duplicates", "params": {}}]}
    body = client.post(
        "/api/v1/preview",
        json={"version_id": version_id, "rule_set": rule, "sample_rows": 10},
        headers=user_headers,
    ).json()
    assert len(body["after_rows"]) == len(body["before_rows"]) - 1
    assert body["affected_row_count"] == 1


def test_preview_sample_rows_is_clamped_and_errors_are_422(client, user_headers):
    _, version_id, _ = _upload(client, user_headers)

    def preview(rule_set, rows=50):
        return client.post(
            "/api/v1/preview",
            json={"version_id": version_id, "rule_set": rule_set, "sample_rows": rows},
            headers=user_headers,
        )

    assert len(preview(TRIM, 0).json()["before_rows"]) == 1
    assert len(preview(TRIM, 99999).json()["before_rows"]) <= 500
    missing = preview({"steps": [{"op": "trim_whitespace", "column": "khong_co"}]})
    assert missing.status_code == 422 and "khong_co" in missing.json()["detail"]
    assert preview({"steps": []}).status_code == 422
    assert preview({"steps": [{"op": "eval", "column": "a"}]}).status_code == 422
    bad_param = preview({"steps": [{"op": "change_case", "column": "ho_ten", "params": {}}]})
    assert bad_param.status_code == 422 and "mode" in bad_param.json()["detail"]


def test_preview_permissions(client, user_headers, other_headers):
    _, version_id, _ = _upload(client, user_headers)
    body = {"version_id": version_id, "rule_set": TRIM}
    assert client.post("/api/v1/preview", json=body).status_code == 401
    assert client.post("/api/v1/preview", json=body, headers=other_headers).status_code == 403
    body["version_id"] = 999999
    assert client.post("/api/v1/preview", json=body, headers=user_headers).status_code == 404


# ---------------------------------------------------------------- apply


def test_apply_creates_new_current_version_with_history(client, db, user_headers, normal_user):
    dataset_id, v1, _ = _upload(client, user_headers)
    response = _apply(client, user_headers, dataset_id, LOWER)
    assert response.status_code == 200, response.text
    v2 = response.json()
    assert v2["version_number"] == 2 and v2["parent_version_id"] == v1
    assert v2["created_by"] == normal_user.id and v2["dataset_id"] == dataset_id
    assert "Chuẩn hóa email (email)" in v2["change_summary"]
    assert _current(client, user_headers, dataset_id) == v2["id"]
    frame = storage.load_dataframe_from_parquet(f"datasets/{dataset_id}/v2.parquet")
    assert frame["email"][1] == "tranthibinh@gmail.com"
    # phiên bản 1 không bị đụng tới
    original = storage.load_dataframe_from_parquet(f"datasets/{dataset_id}/v1.parquet")
    assert original["email"][1] == " TranThiBinh@GMAIL.com "
    op = db.scalars(select(CleaningOperation)).one()
    assert (op.from_version_id, op.to_version_id, op.operation_type) == (
        v1,
        v2["id"],
        "standardize_email",
    )
    assert op.rows_affected >= 1 and op.params["column"] == "email"
    log = db.scalars(select(AuditLog).where(AuditLog.action == "version.apply_rule")).one()
    assert log.new_value["version_number"] == 2


def test_apply_rule_that_fails_leaves_no_trace(client, db, user_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    bad = {
        "steps": [
            {"op": "trim_whitespace", "column": "email"},
            {
                "op": "cast_type",
                "column": "ho_ten",
                "params": {"target_type": "int", "on_error": "raise"},
            },
        ]
    }
    response = _apply(client, user_headers, dataset_id, bad)
    assert response.status_code == 422 and "Bước 2" in response.json()["detail"]
    assert _current(client, user_headers, dataset_id) == v1
    assert (
        len(client.get(f"/api/v1/datasets/{dataset_id}/versions", headers=user_headers).json()) == 1
    )
    assert db.scalar(select(CleaningOperation.id)) is None
    assert not [a for a in db.scalars(select(AuditLog)) if a.action == "version.apply_rule"]


def test_apply_rejects_empty_rules_and_results_without_rows(client, user_headers):
    dataset_id, _, _ = _upload(client, user_headers)
    assert _apply(client, user_headers, dataset_id, {"steps": []}).status_code == 422
    everything = {
        "steps": [
            {"op": "drop_rows_where", "column": "ho_ten", "params": {"operator": "is_not_null"}}
        ]
    }
    empty = _apply(client, user_headers, dataset_id, everything)
    assert empty.status_code == 422 and "không còn dòng" in empty.json()["detail"]


def test_apply_permissions(client, user_headers, other_headers, admin_headers):
    dataset_id, _, _ = _upload(client, user_headers)
    url = f"/api/v1/versions/{dataset_id}/apply"
    assert client.post(url, json=TRIM).status_code == 401
    assert client.post(url, json=TRIM, headers=other_headers).status_code == 403
    assert _apply(client, user_headers, 999999, TRIM).status_code == 404
    assert client.post(url, json=TRIM, headers=admin_headers).status_code == 200


# ---------------------------------------------------------------- undo / redo / restore


def test_undo_redo_cycle_never_deletes_versions(client, db, user_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    v2 = _apply(client, user_headers, dataset_id, LOWER).json()["id"]
    v3 = _apply(client, user_headers, dataset_id, DATES).json()["id"]
    base = f"/api/v1/versions/{dataset_id}"

    assert client.post(f"{base}/undo", headers=user_headers).json()["id"] == v2
    assert _current(client, user_headers, dataset_id) == v2
    assert client.post(f"{base}/undo", headers=user_headers).json()["id"] == v1
    cannot = client.post(f"{base}/undo", headers=user_headers)
    assert cannot.status_code == 422 and "hoàn tác" in cannot.json()["detail"]
    assert client.post(f"{base}/redo", headers=user_headers).json()["id"] == v2
    assert client.post(f"{base}/redo", headers=user_headers).json()["id"] == v3
    nothing = client.post(f"{base}/redo", headers=user_headers)
    assert nothing.status_code == 422 and "làm lại" in nothing.json()["detail"]
    assert (
        len(client.get(f"/api/v1/datasets/{dataset_id}/versions", headers=user_headers).json()) == 3
    )
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert actions.count("version.undo") == 2 and actions.count("version.redo") == 2


def test_apply_after_undo_branches_and_redo_follows_newest_branch(client, user_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    _apply(client, user_headers, dataset_id, LOWER)
    base = f"/api/v1/versions/{dataset_id}"
    client.post(f"{base}/undo", headers=user_headers)
    branch = _apply(client, user_headers, dataset_id, DATES).json()
    assert branch["version_number"] == 3 and branch["parent_version_id"] == v1
    client.post(f"{base}/undo", headers=user_headers)
    assert client.post(f"{base}/redo", headers=user_headers).json()["id"] == branch["id"]


def test_restore_any_version_and_rejects_foreign_versions(client, user_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    v2 = _apply(client, user_headers, dataset_id, LOWER).json()["id"]
    other_dataset, other_version, _ = _upload(client, user_headers)
    base = f"/api/v1/versions/{dataset_id}"
    assert client.post(f"{base}/restore/{v1}", headers=user_headers).json()["id"] == v1
    assert _current(client, user_headers, dataset_id) == v1
    assert client.post(f"{base}/restore/{v2}", headers=user_headers).json()["id"] == v2
    assert client.post(f"{base}/restore/{other_version}", headers=user_headers).status_code == 404
    assert client.post(f"{base}/restore/999999", headers=user_headers).status_code == 404


def test_version_endpoints_permissions(client, user_headers, other_headers):
    dataset_id, v1, _ = _upload(client, user_headers)
    for path in ("undo", "redo", f"restore/{v1}"):
        url = f"/api/v1/versions/{dataset_id}/{path}"
        assert client.post(url).status_code == 401
        assert client.post(url, headers=other_headers).status_code == 403
        assert (
            client.post(url.replace(str(dataset_id), "999999"), headers=user_headers).status_code
            == 404
        )


# ---------------------------------------------------------------- rule template


def test_rule_templates_crud_and_permissions(
    client, db, user_headers, other_headers, admin_headers
):
    _, _, project_id = _upload(client, user_headers)
    url = f"/api/v1/rules/by-project/{project_id}"
    assert client.get(url, headers=user_headers).json() == []
    single = client.post(
        url, json={"name": " Chuẩn hóa email ", "rule_set": LOWER}, headers=user_headers
    )
    assert single.status_code == 200, single.text
    body = single.json()
    assert body["name"] == "Chuẩn hóa email" and body["rule_type"] == "standardize_email"
    assert body["target_column"] == "email" and body["rule_set"] == {
        "steps": [{"op": "standardize_email", "column": "email", "params": {"drop_invalid": False}}]
    }
    multi = client.post(
        url,
        json={"name": "Nhiều bước", "rule_set": {"steps": TRIM["steps"] + DATES["steps"]}},
        headers=user_headers,
    ).json()
    assert multi["rule_type"] == "ruleset" and len(multi["rule_set"]["steps"]) == 2
    assert [r["id"] for r in client.get(url, headers=user_headers).json()] == [
        multi["id"],
        body["id"],
    ]

    assert client.get(url, headers=other_headers).status_code == 403
    assert (
        client.post(url, json={"name": "x", "rule_set": TRIM}, headers=other_headers).status_code
        == 403
    )
    assert client.delete(f"/api/v1/rules/{body['id']}", headers=other_headers).status_code == 403
    assert client.delete(f"/api/v1/rules/{body['id']}").status_code == 401
    assert client.delete("/api/v1/rules/999999", headers=user_headers).status_code == 404

    assert client.delete(f"/api/v1/rules/{body['id']}", headers=user_headers).status_code == 200
    assert client.delete(f"/api/v1/rules/{multi['id']}", headers=admin_headers).status_code == 200
    assert client.get(url, headers=user_headers).json() == []
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert actions.count("rule.create") == 2 and actions.count("rule.delete") == 2


def test_rule_template_validation(client, user_headers):
    _, _, project_id = _upload(client, user_headers)
    url = f"/api/v1/rules/by-project/{project_id}"
    assert (
        client.post(url, json={"name": "  ", "rule_set": TRIM}, headers=user_headers).status_code
        == 422
    )
    assert (
        client.post(
            url, json={"name": "x", "rule_set": {"steps": []}}, headers=user_headers
        ).status_code
        == 422
    )
    bad_op = {"steps": [{"op": "drop_database", "column": "a"}]}
    assert (
        client.post(url, json={"name": "x", "rule_set": bad_op}, headers=user_headers).status_code
        == 422
    )
    assert client.post(url, json={"rule_set": TRIM}, headers=user_headers).status_code == 422


def test_system_rule_can_only_be_deleted_by_admin(
    client, db, user_headers, admin_headers, admin_user
):
    from app.models.rule import Rule

    rule = Rule(
        project_id=None, name="Hệ thống", rule_type="trim_whitespace", target_column="a", params={}
    )
    db.add(rule)
    db.commit()
    assert client.delete(f"/api/v1/rules/{rule.id}", headers=user_headers).status_code == 403
    assert client.delete(f"/api/v1/rules/{rule.id}", headers=admin_headers).status_code == 200


def test_full_flow_on_demo_file_applies_all_suggestions(client, user_headers):
    """Luồng thật: gợi ý -> áp dụng toàn bộ các rule được gợi ý -> dữ liệu sạch hơn."""
    dataset_id, v1, _ = _upload(client, user_headers)
    suggestions = client.post(
        "/api/v1/suggestions/generate", json={"version_id": v1}, headers=user_headers
    ).json()
    steps = []
    for suggestion in suggestions:
        if suggestion["target_column"] == "email" and suggestion["proposed_rule"]["steps"][0][
            "params"
        ].get("drop_invalid"):
            continue  # bước này xóa email sai: người dùng thường bỏ qua
        steps += suggestion["proposed_rule"]["steps"]
    response = _apply(client, user_headers, dataset_id, {"steps": steps})
    assert response.status_code == 200, response.text
    v2 = response.json()
    assert v2["row_count"] == 29  # đã xóa 1 dòng trùng
    frame = storage.load_dataframe_from_parquet(
        f"datasets/{dataset_id}/v{v2['version_number']}.parquet"
    )
    assert set(frame["tinh_thanh"].unique()) & {"HCM", "TP.HCM", "TPHCM"} == set()
    assert all(d == "" or len(d) == 10 for d in frame["ngay_sinh"])  # yyyy-MM-dd hết
    assert all(e == e.strip() for e in frame["email"])
