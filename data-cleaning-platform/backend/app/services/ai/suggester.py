"""Sinh gợi ý làm sạch: quy tắc dựa trên lỗi đã phát hiện (luôn có), AI bổ sung (tùy chọn).

Quy trình: lỗi (data_issues) -> gợi ý theo quy tắc cố định (nhanh, miễn phí, giải thích được)
-> nếu có khóa AI thì hỏi thêm AI trên bản TÓM TẮT đã che thông tin cá nhân -> kiểm tra chặt JSON
của AI -> bỏ gợi ý trùng với quy tắc -> lưu. AI hỏng/không có khóa thì chỉ dùng quy tắc.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.data_issue import DataIssue
from app.models.dataset import DatasetVersion
from app.models.schema_profile import SchemaProfile
from app.models.suggestion import Suggestion
from app.schemas.rule import RuleSet
from app.services import profiling_service
from app.services.ai import service as ai_service
from app.services.ai.explainer import explain_issue
from app.services.ai.masking import mask_sample_values
from app.services.ai.prompts import SUGGESTION_SYSTEM_PROMPT, build_suggestion_prompt
from app.services.ai.validator import AISuggestion, validate_ai_suggestions
from app.services.audit import log_action
from app.services.detectors.base import DetectionIssue
from app.services.frames import load_version_frame
from app.services.rules.engine import dry_run
from app.services.rules.registry import RuleError

logger = logging.getLogger(__name__)
MAX_SUMMARY_ISSUES = 40
AI_CHECK_SAMPLE_ROWS = 1000
_CASE_MODES = {"title": "title", "upper": "upper", "lower": "lower"}


@dataclass
class ProposedSuggestion:
    """Một gợi ý chưa lưu."""

    source: str  # 'rule_engine' | 'ai'
    issue_id: int | None
    target_column: str | None
    rule_set: RuleSet
    explanation: str
    confidence: float | None


def _step(op: str, column: str | None, **params: Any) -> RuleSet:
    return RuleSet.model_validate({"steps": [{"op": op, "column": column, "params": params}]})


def _as_detection(issue: DataIssue) -> DetectionIssue:
    return DetectionIssue(
        issue_type=issue.issue_type,
        column=issue.column_name,
        severity=issue.severity,
        message=issue.message,
        affected_row_indices=[],
        extra=dict(issue.details),
    )


def mask_rule_to_text(rule_set: RuleSet) -> str:
    """Mô tả ngắn một RuleSet, ví dụ 'trim_whitespace(ho_ten) -> change_case(ho_ten)'."""
    return " -> ".join(f"{s.op}({s.column or '*'})" for s in rule_set.steps) or "(trống)"


def rule_for_issue(
    issue: DataIssue, profiles: dict[str, SchemaProfile]
) -> tuple[RuleSet, str, float] | None:
    """(rule, câu mô tả cách xử lý, độ tin cậy) cho một lỗi; None nếu cần người tự xử lý."""
    kind, column = issue.details.get("kind"), issue.column_name
    profile = profiles.get(column) if column else None
    if kind == "missing_values":
        return _missing_rule(issue, profile)
    if kind == "exact_duplicate_rows":
        return (
            _step("drop_duplicates", None, keep="first"),
            "Giữ dòng đầu tiên và xóa các dòng lặp lại.",
            0.9,
        )
    if kind == "iqr_outlier":
        return (
            _step("flag_outliers", column, method="iqr", threshold=1.5),
            "Chỉ đánh dấu các giá trị bất thường vào một cột mới, không xóa hay sửa dữ liệu.",
            0.8,
        )
    if kind == "non_numeric_in_numeric":
        target = "int" if profile and profile.inferred_type == "integer" else "float"
        return (
            _step("cast_type", column, target_type=target, on_error="coerce"),
            "Ép cả cột về dạng số; ô chứa chữ sẽ thành ô trống để dễ thấy và xử lý tiếp.",
            0.75,
        )
    if kind == "mixed_date_format":
        return (
            _step("standardize_date", column, output_format="%Y-%m-%d", dayfirst=True),
            "Đổi mọi ngày về dạng năm-tháng-ngày (yyyy-MM-dd), hiểu số đầu là ngày khi mơ hồ.",
            0.85,
        )
    if kind == "mixed_phone_format":
        shapes = issue.details.get("shapes", {})
        dominant = max(shapes, key=shapes.get) if shapes else ""
        fmt = "E164" if dominant.startswith("quốc tế") else "NATIONAL"
        label = "+84901234567" if fmt == "E164" else "0901234567"
        return (
            _step("standardize_phone", column, region="VN", output_format=fmt),
            f"Đổi mọi số điện thoại hợp lệ về một kiểu duy nhất (ví dụ {label}).",
            0.85,
        )
    if kind == "invalid_email":
        return (
            _step("standardize_email", column, drop_invalid=True),
            "Chuẩn hóa email và đặt ô trống cho email sai cú pháp để không dùng nhầm.",
            0.6,
        )
    if kind == "email_case_whitespace":
        return (
            _step("standardize_email", column, drop_invalid=False),
            "Cắt khoảng trắng và đổi email về chữ thường; email sai cú pháp được giữ nguyên.",
            0.95,
        )
    if kind == "extra_whitespace":
        return (
            _step("trim_whitespace", column),
            "Cắt khoảng trắng đầu/cuối và gộp khoảng trắng thừa ở giữa.",
            0.95,
        )
    if kind == "mixed_case":
        mode = _CASE_MODES.get(str(issue.details.get("dominant_style")))
        if mode is None:
            return None
        names = {"title": "Viết Hoa Đầu Từ", "upper": "IN HOA", "lower": "chữ thường"}
        return (
            _step("change_case", column, mode=mode),
            f"Đổi cả cột về kiểu {names[mode]}, là kiểu phổ biến nhất trong cột.",
            0.7,
        )
    if kind == "value_variants" and issue.details.get("mapping"):
        return (
            _step("replace_values", column, mapping=issue.details["mapping"]),
            "Gộp các cách viết khác nhau về một giá trị chuẩn (xem bảng đổi trong gợi ý).",
            0.85 if issue.details.get("province") else 0.7,
        )
    return None


def _missing_rule(
    issue: DataIssue, profile: SchemaProfile | None
) -> tuple[RuleSet, str, float] | None:
    column = issue.column_name
    if profile is None:
        return None
    ratio = profile.null_ratio
    if profile.inferred_type in ("integer", "float"):
        return (
            _step("fill_missing", column, strategy="median"),
            "Điền các ô thiếu bằng trung vị (giá trị ở giữa) của cột.",
            0.6,
        )
    if profile.inferred_type == "text" and 0 < profile.unique_count <= 20 and ratio <= 0.2:
        return (
            _step("fill_missing", column, strategy="mode"),
            "Điền các ô thiếu bằng giá trị xuất hiện nhiều nhất trong cột.",
            0.5,
        )
    tokens = [t for t in issue.details.get("tokens", {}) if t != "(ô trống)"]
    if tokens:
        return (
            _step("replace_values", column, mapping={t: "" for t in tokens}),
            f"Đổi các dấu thay thế ({', '.join(repr(t) for t in tokens[:4])}) thành ô trống thật "
            "để thống nhất cách ghi ô thiếu.",
            0.8,
        )
    return None


def baseline_suggestions(
    issues: list[DataIssue], profiles: dict[str, SchemaProfile]
) -> list[ProposedSuggestion]:
    """Gợi ý theo quy tắc cho từng lỗi (giữ thứ tự lỗi: nghiêm trọng trước)."""
    proposals = []
    for issue in issues:
        result = rule_for_issue(issue, profiles)
        if result is None:
            continue
        rule_set, fix, confidence = result
        proposals.append(
            ProposedSuggestion(
                source="rule_engine",
                issue_id=issue.id,
                target_column=issue.column_name,
                rule_set=rule_set,
                explanation=f"{explain_issue(_as_detection(issue))} Cách xử lý: {fix}",
                confidence=confidence,
            )
        )
    return proposals


# ---------------------------------------------------------------- phần AI (tùy chọn)


def _example_kind(profile: SchemaProfile | None) -> str | None:
    """Kiểu che dữ liệu cho mẫu giá trị của một cột."""
    if profile is None:
        return None
    if profile.inferred_type in ("email", "phone"):
        return profile.inferred_type
    if profile.inferred_type == "text" and profile.unique_ratio > 0.5:
        return "name"  # cột gần như mỗi dòng một giá trị: nhiều khả năng là tên người/địa chỉ
    return None


def build_profiling_summary(
    row_count: int, profiles: list[SchemaProfile], issues: list[DataIssue]
) -> dict[str, Any]:
    """Tóm tắt gửi cho AI: thống kê cột + lỗi, mẫu giá trị đã che; KHÔNG chứa dòng dữ liệu thật."""
    chosen = profiles[: settings.AI_MAX_COLUMNS]
    by_name = {p.column_name: p for p in chosen}
    columns = []
    for p in chosen:
        entry: dict[str, Any] = {
            "name": p.column_name,
            "type": p.inferred_type,
            "null_ratio": round(p.null_ratio, 3),
            "unique_count": p.unique_count,
        }
        if p.inferred_type == "date":
            entry["format"] = p.detected_format
        else:
            entry["samples"] = mask_sample_values(p.sample_values[:3], _example_kind(p))
        if p.min_value is not None:
            entry.update(min=p.min_value, max=p.max_value, mean=p.mean_value)
        columns.append(entry)
    issue_list = []
    for issue in issues:
        if issue.column_name is not None and issue.column_name not in by_name:
            continue
        kind = _example_kind(by_name.get(issue.column_name))
        issue_list.append(
            {
                "id": issue.id,
                "column": issue.column_name,
                "type": issue.issue_type,
                "kind": issue.details.get("kind"),
                "severity": issue.severity,
                "affected": issue.affected_count,
                # Lỗi cấp dòng (không gắn cột) có ví dụ là cả dòng dữ liệu thật: không gửi cho AI.
                "examples": (
                    mask_sample_values(issue.details.get("examples", [])[:3], kind)
                    if issue.column_name is not None
                    else []
                ),
            }
        )
        if len(issue_list) >= MAX_SUMMARY_ISSUES:
            break
    return {"row_count": row_count, "columns": columns, "issues": issue_list}


def ai_suggestions(
    db: Session,
    user_id: int | None,
    version: DatasetVersion,
    profiles: list[SchemaProfile],
    issues: list[DataIssue],
) -> tuple[list[ProposedSuggestion], str]:
    """Gợi ý bổ sung từ AI và trạng thái AI (disabled/fallback/used).

    Danh sách rỗng nếu không có khóa, AI lỗi hay câu trả lời không hợp lệ.
    """
    if not ai_service.ai_available():
        return [], ai_service.AI_DISABLED
    summary = build_profiling_summary(version.row_count, profiles, issues)
    data = ai_service.call_ai(
        db,
        user_id,
        "suggestions",
        SUGGESTION_SYSTEM_PROMPT,
        build_suggestion_prompt(summary),
    )
    if data is None:
        return [], ai_service.AI_FALLBACK
    columns = {p.column_name for p in profiles}
    valid = validate_ai_suggestions(data, columns, {i.id for i in issues})
    valid = _only_runnable(version, valid)
    proposals = [
        ProposedSuggestion(
            source="ai",
            issue_id=s.issue_id,
            target_column=s.column,
            rule_set=s.rule_set,
            explanation=s.explanation,
            confidence=s.confidence,
        )
        for s in valid
    ]
    return proposals, ai_service.AI_USED


def _only_runnable(version: DatasetVersion, suggestions: list[AISuggestion]) -> list[AISuggestion]:
    """Bỏ gợi ý của AI mà Rule Engine không chạy nổi (tham số sai...), thử trên một mẫu dữ liệu."""
    if not suggestions:
        return []
    sample = load_version_frame(version).head(AI_CHECK_SAMPLE_ROWS)
    runnable = []
    for suggestion in suggestions:
        try:
            dry_run(sample, suggestion.rule_set)
        except RuleError as exc:
            logger.info("Bỏ gợi ý AI không chạy được: %s", exc)
            continue
        runnable.append(suggestion)
    return runnable


def _fingerprint(rule_set: RuleSet) -> str:
    return json.dumps(rule_set.model_dump(mode="json")["steps"], sort_keys=True, ensure_ascii=False)


def merge_proposals(
    baseline: list[ProposedSuggestion], extra: list[ProposedSuggestion]
) -> list[ProposedSuggestion]:
    """Quy tắc trước, rồi gợi ý AI không trùng nội dung với bất kỳ gợi ý nào đã có."""
    seen = {_fingerprint(p.rule_set) for p in baseline}
    merged = list(baseline)
    for proposal in extra:
        fingerprint = _fingerprint(proposal.rule_set)
        if fingerprint not in seen:
            seen.add(fingerprint)
            merged.append(proposal)
    return merged


# ---------------------------------------------------------------- điểm vào


def generate_suggestions(
    db: Session, user_id: int, version: DatasetVersion, ip_address: str | None = None
) -> tuple[list[Suggestion], str]:
    """Sinh lại toàn bộ gợi ý của phiên bản (thay thế gợi ý cũ).

    Trả (danh sách đã lưu, trạng thái AI: disabled/fallback/used).
    """
    profiles = profiling_service.run_profiling(db, version)  # tự chạy profiling nếu chưa có
    issues = profiling_service.list_issue_rows(db, version.id)
    by_name = {p.column_name: p for p in profiles}

    ai_proposals, ai_status = ai_suggestions(db, user_id, version, profiles, issues)
    proposals = merge_proposals(baseline_suggestions(issues, by_name), ai_proposals)

    db.get(DatasetVersion, version.id, with_for_update=True)
    db.execute(delete(Suggestion).where(Suggestion.version_id == version.id))
    saved = []
    for proposal in proposals:
        suggestion = Suggestion(
            version_id=version.id,
            issue_id=proposal.issue_id,
            suggestion_type="fix" if proposal.issue_id else "rule",
            source=proposal.source,
            target_column=proposal.target_column,
            proposed_rule=proposal.rule_set.model_dump(mode="json"),
            explanation=proposal.explanation,
            confidence=proposal.confidence,
            status="pending",
        )
        db.add(suggestion)
        saved.append(suggestion)
    log_action(
        db,
        user_id,
        "suggestion.generate",
        "dataset",
        version.dataset_id,
        project_id=version.dataset.project_id,
        new_value={
            "version_id": version.id,
            "count": len(saved),
            "ai": sum(1 for p in proposals if p.source == "ai"),
        },
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    stmt = select(Suggestion).where(Suggestion.version_id == version.id).order_by(Suggestion.id)
    return list(db.scalars(stmt)), ai_status
