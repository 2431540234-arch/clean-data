"""Nhóm 5 - gợi ý làm sạch: quy tắc, AI tùy chọn (client giả), quyết định, quyền, mapping tầng 2."""

import json

from sqlalchemy import select

from app.models.ai_request import AIRequest
from app.models.audit_log import AuditLog
from app.models.suggestion import Suggestion
from app.services.ai import client as client_module
from app.services.ai import service as ai_service
from app.services.ai.client import AIError, AIResponse
from tests.conftest import FIXTURES_DIR

DIRTY = (FIXTURES_DIR / "dirty_sample.csv").read_bytes()
SAMPLE = FIXTURES_DIR.parent.parent.parent / "sample_data" / "khach_hang_ban.csv"


def _upload(client, headers, content=DIRTY, name="dirty_sample.csv"):
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()["id"]
    response = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": (name, content)},
        headers=headers,
    )
    return response.json()["first_version"]["id"]


def _generate(client, headers, version_id):
    return client.post(
        "/api/v1/suggestions/generate", json={"version_id": version_id}, headers=headers
    )


class FakeAI(client_module.AIClient):
    """Client AI giả: không gọi mạng, ghi lại prompt, trả dữ liệu hoặc ném lỗi theo kịch bản."""

    def __init__(self, data=None, error=None, configured=True):
        super().__init__("anthropic")
        self.data, self.error, self.configured = data, error, configured
        self.prompts: list[tuple[str, str]] = []

    def is_configured(self):
        return self.configured

    def complete_json(self, system_prompt, user_prompt):
        self.prompts.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return AIResponse(self.data, "anthropic", "mo-hinh-gia", 100, 50, 123)


def _use_ai(monkeypatch, fake):
    monkeypatch.setattr(ai_service, "get_client", lambda: fake)
    return fake


# ---------------------------------------------------------------- quy tắc (không có AI)


def test_generate_rule_suggestions_for_dirty_file(client, db, user_headers):
    version_id = _upload(client, user_headers)
    response = _generate(client, user_headers, version_id)
    assert response.status_code == 200, response.text
    suggestions = response.json()
    assert suggestions and all(s["source"] == "rule_engine" for s in suggestions)
    assert all(s["status"] == "pending" and s["version_id"] == version_id for s in suggestions)
    assert all(s["issue_id"] is not None and s["explanation"] for s in suggestions)

    by_op = {s["proposed_rule"]["steps"][0]["op"]: s for s in suggestions}
    assert {"drop_duplicates", "standardize_date", "replace_values", "standardize_phone"} <= set(
        by_op
    )
    date = by_op["standardize_date"]["proposed_rule"]["steps"][0]
    assert date == {
        "op": "standardize_date",
        "column": "ngay_sinh",
        "params": {"output_format": "%Y-%m-%d", "dayfirst": True},
    }
    mapping = by_op["replace_values"]["proposed_rule"]["steps"][0]["params"]["mapping"]
    assert mapping["HCM"] == "TP. Hồ Chí Minh"
    assert by_op["flag_outliers"]["target_column"] == "tuoi"
    assert 0 <= by_op["drop_duplicates"]["confidence"] <= 1
    assert "Cách xử lý" in by_op["drop_duplicates"]["explanation"]


def test_generate_replaces_old_suggestions_not_accumulates(client, db, user_headers):
    version_id = _upload(client, user_headers)
    first = _generate(client, user_headers, version_id).json()
    second = _generate(client, user_headers, version_id).json()
    assert len(first) == len(second)
    assert not ({s["id"] for s in first} & {s["id"] for s in second})
    listed = client.get(f"/api/v1/suggestions/by-version/{version_id}", headers=user_headers).json()
    assert [s["id"] for s in listed] == [s["id"] for s in second]


def test_generate_runs_profiling_automatically(client, user_headers):
    version_id = _upload(client, user_headers)
    assert client.get(f"/api/v1/profiling/{version_id}", headers=user_headers).status_code == 404
    _generate(client, user_headers, version_id)
    assert client.get(f"/api/v1/profiling/{version_id}", headers=user_headers).status_code == 200


def test_clean_file_gives_empty_list(client, user_headers):
    version_id = _upload(client, user_headers, b"ten,tuoi\nAn,29\nBinh,34\nCuong,37\n", "s.csv")
    assert _generate(client, user_headers, version_id).json() == []
    listed = client.get(f"/api/v1/suggestions/by-version/{version_id}", headers=user_headers)
    assert listed.status_code == 200 and listed.json() == []


def test_missing_values_rules_depend_on_column_type(client, user_headers):
    rows = ["ten,tuoi,ghi_chu"] + [f"A{i},{20 + i},x" for i in range(10)]
    rows += ["B1,,N/A", "B2,N/A,-"]
    version_id = _upload(client, user_headers, "\n".join(rows).encode(), "m.csv")
    steps = [
        s["proposed_rule"]["steps"][0] for s in _generate(client, user_headers, version_id).json()
    ]
    age = next(s for s in steps if s["column"] == "tuoi" and s["op"] == "fill_missing")
    assert age["params"] == {"strategy": "median"}


def test_accept_reject_and_change_mind_with_audit(client, db, user_headers, normal_user):
    version_id = _upload(client, user_headers)
    suggestion_id = _generate(client, user_headers, version_id).json()[0]["id"]
    url = f"/api/v1/suggestions/{suggestion_id}/decision"
    accepted = client.post(url, json={"decision": "accepted"}, headers=user_headers)
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "accepted" and body["reviewed_by"] == normal_user.id
    assert body["reviewed_at"] is not None
    rejected = client.post(url, json={"decision": "rejected"}, headers=user_headers).json()
    assert rejected["status"] == "rejected"
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert actions[-2:] == ["suggestion.accept", "suggestion.reject"]
    assert client.post(url, json={"decision": "maybe"}, headers=user_headers).status_code == 422
    # chấp nhận không tạo version mới
    assert (
        len(
            client.get(
                f"/api/v1/datasets/{_dataset_of(client, user_headers, version_id)}/versions",
                headers=user_headers,
            ).json()
        )
        == 1
    )


def _dataset_of(client, headers, version_id):
    # version -> dataset qua profiling-free lookup: dùng DB-free cách đơn giản là danh sách project
    projects = client.get("/api/v1/projects", headers=headers).json()
    for project in projects:
        for dataset in client.get(
            f"/api/v1/projects/{project['id']}/datasets", headers=headers
        ).json():
            if dataset["current_version_id"] == version_id:
                return dataset["id"]
    raise AssertionError("không tìm thấy dataset")


def test_permissions(client, user_headers, other_headers, admin_headers):
    version_id = _upload(client, user_headers)
    suggestion_id = _generate(client, user_headers, version_id).json()[0]["id"]
    generate = {"version_id": version_id}
    assert client.post("/api/v1/suggestions/generate", json=generate).status_code == 401
    assert (
        client.post(
            "/api/v1/suggestions/generate", json=generate, headers=other_headers
        ).status_code
        == 403
    )
    assert _generate(client, user_headers, 999999).status_code == 404
    listing = f"/api/v1/suggestions/by-version/{version_id}"
    assert client.get(listing, headers=other_headers).status_code == 403
    decision = f"/api/v1/suggestions/{suggestion_id}/decision"
    assert (
        client.post(decision, json={"decision": "accepted"}, headers=other_headers).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/suggestions/999999/decision",
            json={"decision": "accepted"},
            headers=user_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(decision, json={"decision": "accepted"}, headers=admin_headers).status_code
        == 200
    )


# ---------------------------------------------------------------- AI tùy chọn


def test_without_api_key_no_ai_request_is_logged(client, db, user_headers):
    _generate(client, user_headers, _upload(client, user_headers))
    assert db.scalar(select(AIRequest.id)) is None


def _ai_payload(issue_id, column="tuoi"):
    return {
        "suggestions": [
            {
                "issue_id": issue_id,
                "column": column,
                "explanation": "AI: đổi tên cột tuổi sang tiếng Anh.",
                "confidence": 0.8,
                "rule": {
                    "steps": [
                        {"op": "rename_column", "column": column, "params": {"new_name": "age"}}
                    ]
                },
            }
        ]
    }


def test_ai_suggestions_are_added_after_rules_and_logged(client, db, user_headers, monkeypatch):
    version_id = _upload(client, user_headers)
    fake = _use_ai(monkeypatch, FakeAI(data=_ai_payload(None)))
    suggestions = _generate(client, user_headers, version_id).json()
    ai = [s for s in suggestions if s["source"] == "ai"]
    assert len(ai) == 1 and ai[0]["target_column"] == "tuoi"
    assert suggestions.index(ai[0]) >= len([s for s in suggestions if s["source"] == "rule_engine"])
    assert ai[0]["suggestion_type"] == "rule" and ai[0]["confidence"] == 0.8
    log = db.scalars(select(AIRequest)).one()
    assert (log.status, log.purpose, log.input_tokens, log.output_tokens) == (
        "success",
        "suggestions",
        100,
        50,
    )
    assert log.user_id is not None and log.model == "mo-hinh-gia" and log.latency_ms == 123
    # tóm tắt gửi AI không chứa dữ liệu cá nhân thật
    prompt = fake.prompts[0][1]
    for secret in ["nguyenvanan@gmail.com", "TranThiBinh", "0912 345 678", "Nguyen Van An"]:
        assert secret not in prompt
    assert "tinh_thanh" in prompt and "iqr_outlier" in prompt


def test_ai_duplicate_of_rule_suggestion_is_dropped(client, user_headers, monkeypatch):
    version_id = _upload(client, user_headers)
    duplicate = {
        "suggestions": [
            {
                "issue_id": None,
                "column": "ngay_sinh",
                "explanation": "trùng với quy tắc",
                "rule": {
                    "steps": [
                        {
                            "op": "standardize_date",
                            "column": "ngay_sinh",
                            "params": {"output_format": "%Y-%m-%d", "dayfirst": True},
                        }
                    ]
                },
            }
        ]
    }
    _use_ai(monkeypatch, FakeAI(data=duplicate))
    suggestions = _generate(client, user_headers, version_id).json()
    assert [s["source"] for s in suggestions].count("ai") == 0


def test_ai_failure_falls_back_to_rules_silently(client, db, user_headers, monkeypatch):
    version_id = _upload(client, user_headers)
    _use_ai(monkeypatch, FakeAI(error=AIError("Hết thời gian chờ AI.", latency_ms=20000)))
    response = _generate(client, user_headers, version_id)
    assert response.status_code == 200 and response.json()
    assert all(s["source"] == "rule_engine" for s in response.json())
    log = db.scalars(select(AIRequest)).one()
    assert (
        log.status == "error" and "Hết thời gian" in log.error_message and log.latency_ms == 20000
    )


def test_ai_suggestion_with_unrunnable_params_is_dropped(client, user_headers, monkeypatch):
    version_id = _upload(client, user_headers)
    unrunnable = {
        "suggestions": [
            {
                "issue_id": None,
                "column": "ho_ten",
                "explanation": "mode sai",
                "rule": {
                    "steps": [
                        {"op": "change_case", "column": "ho_ten", "params": {"mode": "rainbow"}}
                    ]
                },
            },
            _ai_payload(None)["suggestions"][0],
        ]
    }
    _use_ai(monkeypatch, FakeAI(data=unrunnable))
    ai = [s for s in _generate(client, user_headers, version_id).json() if s["source"] == "ai"]
    assert [s["target_column"] for s in ai] == ["tuoi"]


def test_ai_garbage_output_is_ignored(client, db, user_headers, monkeypatch):
    version_id = _upload(client, user_headers)
    bad = {
        "suggestions": [{"rule": {"steps": [{"op": "__import__('os')", "column": "x"}]}}, 5, None]
    }
    _use_ai(monkeypatch, FakeAI(data=bad))
    response = _generate(client, user_headers, version_id)
    assert response.status_code == 200
    assert all(s["source"] == "rule_engine" for s in response.json())


def test_unconfigured_ai_is_skipped(client, db, user_headers, monkeypatch):
    fake = _use_ai(monkeypatch, FakeAI(data=_ai_payload(None), configured=False))
    _generate(client, user_headers, _upload(client, user_headers))
    assert fake.prompts == [] and db.scalar(select(AIRequest.id)) is None


def test_total_ai_calls_counts_requests(client, db, user_headers, monkeypatch):
    _use_ai(monkeypatch, FakeAI(data=_ai_payload(None)))
    _generate(client, user_headers, _upload(client, user_headers))
    assert len(db.scalars(select(AIRequest)).all()) == 1


# ---------------------------------------------------------------- mapping tầng 2


def test_mapping_uses_ai_for_unmatched_columns_only_with_valid_targets(
    client, db, user_headers, monkeypatch
):
    content = b"ma_so,quoc_gia,cot_la\n1,VN,x\n2,US,y\n"
    version_id = _upload(client, user_headers, content, "m.csv")
    answer = {"mapping": {"ma_so": "ma_khach_hang", "quoc_gia": "ten_khong_hop_le", "cot_la": None}}
    fake = _use_ai(monkeypatch, FakeAI(data=answer))
    response = client.post(
        f"/api/v1/mapping/{version_id}/suggest",
        json=["ma_khach_hang", "country"],
        headers=user_headers,
    )
    assert response.json() == {"ma_so": "ma_khach_hang", "quoc_gia": None, "cot_la": None}
    assert "1,VN" not in fake.prompts[0][1]  # chỉ gửi tên cột
    assert db.scalars(select(AIRequest)).one().purpose == "column_mapping"


def test_mapping_skips_ai_when_everything_matched(client, db, user_headers, monkeypatch):
    version_id = _upload(client, user_headers, b"ho_ten,email\nA,a@x.vn\n", "m.csv")
    fake = _use_ai(monkeypatch, FakeAI(data={"mapping": {}}))
    response = client.post(
        f"/api/v1/mapping/{version_id}/suggest", json=["ho_ten", "email"], headers=user_headers
    )
    assert response.json() == {"ho_ten": "ho_ten", "email": "email"} and fake.prompts == []


def test_prompt_is_valid_json_summary(client, user_headers, monkeypatch):
    version_id = _upload(client, user_headers)
    fake = _use_ai(monkeypatch, FakeAI(data={"suggestions": []}))
    _generate(client, user_headers, version_id)
    prompt = fake.prompts[0][1]
    summary = json.loads(prompt[prompt.index("{") : prompt.index("\n\n")])
    assert summary["row_count"] > 0 and summary["columns"] and summary["issues"]
    everything = json.dumps(summary, ensure_ascii=False)
    assert "nguyenvanan" not in everything and "TranThiBinh" not in everything
    assert db_free_assert_columns_limit(summary)


def db_free_assert_columns_limit(summary) -> bool:
    return len(summary["columns"]) <= 40


def test_suggestion_rows_store_valid_rulesets(client, db, user_headers):
    version_id = _upload(client, user_headers)
    _generate(client, user_headers, version_id)
    from app.schemas.rule import RuleSet

    for row in db.scalars(select(Suggestion)):
        assert RuleSet.model_validate(row.proposed_rule).steps
