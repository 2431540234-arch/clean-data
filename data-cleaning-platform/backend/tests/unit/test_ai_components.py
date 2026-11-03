"""Thành phần AI: che dữ liệu, parse/kiểm tra JSON, client (SDK giả), kiểm tra gợi ý của AI."""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.ai import client as client_module
from app.services.ai.client import AIClient, AIError, parse_json_object
from app.services.ai.masking import mask_sample_values, mask_value
from app.services.ai.validator import (
    AIRuleValidationError,
    validate_ai_rule_json,
    validate_ai_suggestions,
)

# ---------------------------------------------------------------- che dữ liệu


def test_mask_email_phone_and_name():
    assert mask_value("nguyenvanan@gmail.com") == "n***@gmail.com"
    assert mask_value("0901234567") == "090***67"
    assert mask_value("+84 933 445 566") == "+84***66"
    assert mask_value("Nguyễn Văn An", "name") == "N. V. A."
    assert mask_value("Hà Nội") == "Hà Nội"  # giá trị phân loại không phải PII
    assert mask_value("") == ""


def test_masked_values_do_not_leak_original():
    masked = mask_sample_values(["tranthibinh@gmail.com", "0912345678"])
    assert "tranthibinh" not in " ".join(masked) and "912345" not in " ".join(masked)


# ---------------------------------------------------------------- parse JSON


def test_parse_json_object_tolerates_fences_and_chatter():
    assert parse_json_object('{"a": 1}') == {"a": 1}
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Đây là kết quả:\n{"a": {"b": 2}}\nHết.') == {"a": {"b": 2}}


@pytest.mark.parametrize("text", ["", "không có json", "{hỏng", "[1, 2]"])
def test_parse_json_object_rejects_garbage(text):
    with pytest.raises(AIError):
        parse_json_object(text)


# ---------------------------------------------------------------- client


class _FakeAnthropicModule:
    """Thay module anthropic: ghi lại tham số và trả câu trả lời cố định."""

    def __init__(self, text='{"ok": true}', error=None):
        self.calls = []
        self._text, self._error = text, error
        outer = self

        class Anthropic:
            def __init__(self, **kwargs):
                outer.client_kwargs = kwargs
                self.messages = SimpleNamespace(create=self.create)

            def create(self, **kwargs):
                outer.calls.append(kwargs)
                if outer._error:
                    raise outer._error
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text=outer._text)],
                    usage=SimpleNamespace(input_tokens=11, output_tokens=7),
                )

        self.Anthropic = Anthropic


def test_client_requires_key(monkeypatch):
    client = AIClient("anthropic")
    assert not client.is_configured()
    with pytest.raises(AIError, match="khóa API"):
        client.complete_json("s", "u")
    assert not AIClient("không-có-provider").is_configured()


def test_anthropic_call_returns_data_and_usage(monkeypatch):
    fake = _FakeAnthropicModule('```json\n{"suggestions": []}\n```')
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "khoa-gia")
    monkeypatch.setattr(settings, "AI_MODEL", "mo-hinh-thu")
    response = AIClient("anthropic").complete_json("hệ thống", "người dùng")
    assert response.data == {"suggestions": []}
    assert (response.input_tokens, response.output_tokens) == (11, 7)
    assert response.model == "mo-hinh-thu" and response.provider == "anthropic"
    assert fake.calls[0]["model"] == "mo-hinh-thu" and fake.calls[0]["system"] == "hệ thống"
    assert fake.client_kwargs["timeout"] == settings.AI_TIMEOUT_SECONDS


def test_client_error_message_never_contains_key(monkeypatch):
    class APIConnectionError(Exception):  # tên giống lỗi tạm thời của SDK -> sẽ thử lại
        pass

    fake = _FakeAnthropicModule(error=APIConnectionError("kết nối hỏng khoa-bi-mat-123"))
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "khoa-bi-mat-123")
    monkeypatch.setattr(client_module.AIClient._call_with_retry.retry, "wait", lambda *_: 0)
    with pytest.raises(AIError) as info:
        AIClient("anthropic").complete_json("s", "u")
    assert "khoa-bi-mat-123" not in str(info.value)
    assert len(fake.calls) == 2  # lỗi tạm thời: đúng 2 lần thử


def test_non_transient_error_is_not_retried(monkeypatch):
    fake = _FakeAnthropicModule(error=ValueError("sai"))
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k")
    with pytest.raises(AIError):
        AIClient("anthropic").complete_json("s", "u")
    assert len(fake.calls) == 1


def test_bad_json_from_model_raises_ai_error(monkeypatch):
    fake = _FakeAnthropicModule("xin lỗi, tôi không làm được")
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k")
    with pytest.raises(AIError):
        AIClient("anthropic").complete_json("s", "u")


# ---------------------------------------------------------------- validator


def test_validate_ai_rule_json():
    rule = validate_ai_rule_json({"steps": [{"op": "trim_whitespace", "column": "a"}]})
    assert rule.steps[0].op == "trim_whitespace"
    for bad in [
        {"steps": [{"op": "exec_python", "column": "a"}]},  # op lạ
        {"steps": [{"op": "trim_whitespace"}]},  # thiếu cột
        {"steps": "không phải danh sách"},
    ]:
        with pytest.raises(AIRuleValidationError):
            validate_ai_rule_json(bad)


def _suggestion(**overrides):
    base = {
        "issue_id": 1,
        "column": "ten",
        "explanation": "Cắt khoảng trắng.",
        "confidence": 0.9,
        "rule": {"steps": [{"op": "trim_whitespace", "column": "ten", "params": {}}]},
    }
    base.update(overrides)
    return base


def test_validate_ai_suggestions_keeps_good_and_drops_bad_individually():
    raw = {
        "suggestions": [
            _suggestion(),
            _suggestion(
                rule={"steps": [{"op": "drop_column", "column": "ten"}]}
            ),  # AI không được xóa cột
            _suggestion(rule={"steps": [{"op": "trim_whitespace", "column": "khong_co"}]}),
            _suggestion(rule={"steps": []}),
            _suggestion(explanation=""),
            _suggestion(rule={"steps": [{"op": "os_system", "column": "ten"}]}),
            "không phải object",
            _suggestion(issue_id=999, confidence=7),  # issue lạ -> None, confidence kẹp về 1.0
        ]
    }
    result = validate_ai_suggestions(raw, {"ten"}, {1})
    assert len(result) == 2
    assert result[0].issue_id == 1 and result[0].confidence == 0.9
    assert result[1].issue_id is None and result[1].confidence == 1.0


def test_validate_ai_suggestions_handles_garbage_and_limits():
    assert validate_ai_suggestions({}, {"ten"}, set()) == []
    assert validate_ai_suggestions({"suggestions": "x"}, {"ten"}, set()) == []
    many = {"suggestions": [_suggestion() for _ in range(30)]}
    assert len(validate_ai_suggestions(many, {"ten"}, {1})) == 8
    long_text = _suggestion(explanation="x" * 2000)
    assert (
        len(validate_ai_suggestions({"suggestions": [long_text]}, {"ten"}, {1})[0].explanation)
        == 500
    )
