"""Detector phát hiện biến thể giá trị không nhất quán, ví dụ "HCM" / "TP.HCM" / "Hồ Chí Minh"."""

import json
from collections import Counter
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz

from app.services.detectors.base import BaseDetector, DetectionIssue, severity_by_ratio
from app.services.profiling.values import DATA_DIR, normalize_key, null_mask

MAX_DISTINCT = 100  # chỉ xét cột phân loại (ít giá trị khác nhau, lặp lại nhiều)
MAX_UNIQUE_RATIO = 0.5
FUZZY_SCORE = 90  # độ giống tối thiểu để gộp hai cách viết gần giống (lỗi gõ nhẹ)
FUZZY_MIN_LENGTH = 5
PROVINCE_SHARE = 0.3  # tỉ lệ giá trị khớp danh sách tỉnh/thành để coi cột là cột tỉnh/thành
_PROVINCE_PREFIXES = ("thanhpho", "tinh", "tp")
_SKIPPED_TYPES = {"email", "phone", "date", "integer", "float", "boolean"}


def province_key(value: str) -> str:
    """Khóa so khớp tỉnh/thành: bỏ dấu/hoa thường/dấu câu và tiền tố 'TP.'/'Thành phố'/'Tỉnh'."""
    key = normalize_key(value)
    for prefix in _PROVINCE_PREFIXES:
        if key.startswith(prefix) and len(key) > len(prefix):
            return key[len(prefix) :]
    return key


@lru_cache(maxsize=1)
def province_lookup() -> dict[str, str]:
    """province_key (của tên chuẩn và mọi alias) -> tên chuẩn."""
    with open(DATA_DIR / "provinces_vn.json", encoding="utf-8") as file:
        provinces = json.load(file)["provinces"]
    lookup: dict[str, str] = {}
    for item in provinces:
        canonical = item["canonical_name"]
        for name in [canonical, *item.get("aliases", [])]:
            lookup.setdefault(province_key(name), canonical)
    return lookup


def _group_by_key(values: list[str], key_of) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for value in values:
        groups.setdefault(key_of(value), []).append(value)
    return groups


def _merge_similar(groups: dict[str, list[str]]) -> dict[str, list[str]]:
    """Gộp các nhóm có khóa gần giống nhau (lỗi gõ nhẹ: 'hanoi' ~ 'hanoii')."""
    keys = [k for k in groups if len(k) >= FUZZY_MIN_LENGTH]
    parent = {k: k for k in keys}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if fuzz.ratio(a, b) >= FUZZY_SCORE:
                parent[find(b)] = find(a)
    merged: dict[str, list[str]] = {}
    for key, variants in groups.items():
        merged.setdefault(find(key) if key in parent else key, []).extend(variants)
    return merged


class InconsistencyDetector(BaseDetector):
    """Phát hiện các giá trị là biến thể của nhau (viết tắt, bỏ dấu, sai chính tả nhẹ)."""

    name = "inconsistency"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Mỗi cột phân loại có biến thể cho cùng một giá trị -> một DetectionIssue."""
        types = self.types_of(df, column_types)
        issues = []
        for column in df.columns:
            if types[column] in _SKIPPED_TYPES:
                continue
            series = df[column]
            present = series[~null_mask(series)].astype(str).str.strip()
            distinct = present.unique().tolist()
            if len(distinct) < 2 or len(distinct) > MAX_DISTINCT:
                continue
            issue = self._analyze(str(column), present, distinct)
            if issue:
                issues.append(issue)
        return issues

    @staticmethod
    def _analyze(column: str, present: pd.Series, distinct: list[str]) -> DetectionIssue | None:
        lookup = province_lookup()
        matched = sum(1 for v in present if province_key(v) in lookup)
        is_province = matched / len(present) >= PROVINCE_SHARE
        # Cột phân loại thông thường phải lặp lại nhiều (tên người thì mỗi dòng một khác: bỏ qua);
        # cột tỉnh/thành luôn được xét vì có danh sách tên chuẩn để đối chiếu.
        if not is_province and len(distinct) / len(present) > MAX_UNIQUE_RATIO:
            return None
        if is_province:
            groups = _group_by_key(
                distinct, lambda v: lookup.get(province_key(v), normalize_key(v))
            )
        else:
            groups = _merge_similar(_group_by_key(distinct, normalize_key))
        counts = Counter(present)

        mapping: dict[str, str] = {}
        report_groups = []
        for key, variants in groups.items():
            if len(variants) < 2:
                continue
            canonical = key if is_province and key in lookup.values() else None
            if canonical is None:
                canonical = max(variants, key=lambda v: (counts[v], -variants.index(v)))
            for variant in variants:
                if variant != canonical:
                    mapping[variant] = canonical
            report_groups.append(
                {"canonical": canonical, "variants": {v: int(counts[v]) for v in variants}}
            )
        if not mapping:
            return None

        affected = present[present.isin(mapping)]
        shown = "; ".join(
            f"{' / '.join(repr(v) for v in g['variants'])} → {g['canonical']!r}"
            for g in report_groups[:3]
        )
        return DetectionIssue(
            issue_type="inconsistent",
            column=column,
            severity=severity_by_ratio(len(affected) / len(present), high=0.3, medium=0.1),
            message=(
                f"Cột '{column}' có {len(mapping)} cách viết khác nhau cho các giá trị đã có: "
                f"{shown}."
            ),
            affected_row_indices=[int(i) for i in affected.index],
            extra={
                "kind": "value_variants",
                "province": is_province,
                "groups": report_groups,
                "mapping": mapping,
                "examples": list(mapping)[:5],
            },
        )
