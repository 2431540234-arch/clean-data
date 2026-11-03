"""Mapping cột tầng 1: fuzzy matching giữa tên cột trong file upload và schema mong muốn."""

from rapidfuzz import fuzz

from app.services.mapping.normalizer import normalize_column_name
from app.services.mapping.synonyms import find_canonical_name

FUZZY_THRESHOLD = 80  # điểm giống tối thiểu (0-100) để nhận một cặp tên gần giống
EXACT_SCORE = 100
SYNONYM_SCORE = 95
CONTAINS_SCORE = 85  # tên nguồn chứa đủ các từ của tên đích ('email_lien_he' chứa 'email')


def _contains_run(words: list[str], run: list[str]) -> bool:
    """`run` xuất hiện liền nhau trong `words` (theo từ, không theo ký tự)."""
    return any(words[i : i + len(run)] == run for i in range(len(words) - len(run) + 1))


def _score(source_norm: str, source_canonical: str | None, target_norm: str) -> float:
    """Điểm khớp của một cặp (cột nguồn, cột đích); 0 nếu không đủ tin cậy."""
    if not source_norm or not target_norm:
        return 0.0
    if source_norm == target_norm:
        return EXACT_SCORE
    target_canonical = find_canonical_name(target_norm)
    # Hai tên cùng thuộc một nhóm đồng nghĩa ("sdt" và "phone_number" đều là so_dien_thoai).
    if source_canonical and target_canonical and source_canonical == target_canonical:
        return SYNONYM_SCORE
    if source_canonical and normalize_column_name(source_canonical) == target_norm:
        return SYNONYM_SCORE
    source_words, target_words = source_norm.split("_"), target_norm.split("_")
    if len(target_norm) >= 3 and _contains_run(source_words, target_words):
        return CONTAINS_SCORE
    fuzzy = fuzz.ratio(source_norm, target_norm)
    return float(fuzzy) if fuzzy >= FUZZY_THRESHOLD else 0.0


def match_columns(source_columns: list[str], target_schema: list[str]) -> dict[str, str | None]:
    """Gợi ý mapping cột nguồn -> cột đích bằng kết hợp synonyms + fuzzy matching.

    Thứ tự tin cậy: trùng tên sau chuẩn hóa (100) > cùng nhóm đồng nghĩa (95) > chứa đủ từ của
    cột đích (85) > gần giống (>= 80).
    Mỗi cột đích chỉ được một cột nguồn; khi tranh chấp, cặp điểm cao hơn thắng (hòa thì cột nguồn
    đứng trước). Kết quả có đủ mọi cột nguồn theo đúng thứ tự, cột không khớp được là None.
    """
    result: dict[str, str | None] = {source: None for source in source_columns}
    targets = [(target, normalize_column_name(target)) for target in dict.fromkeys(target_schema)]
    candidates: list[tuple[float, int, int]] = []
    for s_index, source in enumerate(source_columns):
        source_norm = normalize_column_name(source)
        source_canonical = find_canonical_name(source_norm)
        for t_index, (_, target_norm) in enumerate(targets):
            score = _score(source_norm, source_canonical, target_norm)
            if score:
                candidates.append((score, s_index, t_index))
    used_sources: set[int] = set()
    used_targets: set[int] = set()
    for _score_value, s_index, t_index in sorted(candidates, key=lambda c: (-c[0], c[1], c[2])):
        if s_index in used_sources or t_index in used_targets:
            continue
        used_sources.add(s_index)
        used_targets.add(t_index)
        result[source_columns[s_index]] = targets[t_index][0]
    return result
