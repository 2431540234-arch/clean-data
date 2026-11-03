"""Op đánh dấu giá trị bất thường (không xóa hay sửa dữ liệu gốc)."""

from typing import Any

import pandas as pd

from app.services.profiling.values import is_null, to_number
from app.services.rules.ops.common import cell_text, require_choice, require_column
from app.services.rules.registry import RuleError, register

METHODS = ("iqr", "zscore")
MIN_VALUES = 4  # ít hơn thì không đủ dữ liệu để nói giá trị nào bất thường
DEFAULT_THRESHOLD = {"iqr": 1.5, "zscore": 3.0}
FLAG_SUFFIX = "_is_outlier"


@register("flag_outliers")
def flag_outliers(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Thêm cột "<cột>_is_outlier" ("True"/"False") đánh dấu giá trị bất thường.

    params:
        method: "iqr" (mặc định; ngoài [Q1 - t*IQR, Q3 + t*IQR]) hoặc "zscore" (|z| > t).
        threshold: t, mặc định 1.5 cho iqr và 3 cho zscore.
    Ô thiếu hoặc không phải số luôn là "False". Số dòng ảnh hưởng là số dòng được đánh dấu.
    """
    require_column(df, column)
    method = require_choice(params, "method", METHODS, "iqr")
    try:
        threshold = float(params.get("threshold", DEFAULT_THRESHOLD[method]))
    except (TypeError, ValueError) as exc:
        raise RuleError("threshold phải là một số.") from exc
    if threshold <= 0:
        raise RuleError("threshold phải lớn hơn 0.")

    texts = df[column].map(cell_text)
    numeric = texts.map(lambda v: None if is_null(v) else to_number(v)).astype(float)
    valid = numeric.dropna()
    flagged = pd.Series(False, index=df.index)
    if len(valid) >= MIN_VALUES:
        if method == "iqr":
            q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
            spread = threshold * (q3 - q1)
            flagged = (numeric < q1 - spread) | (numeric > q3 + spread)
        else:
            std = valid.std()
            if std:
                flagged = (numeric - valid.mean()).abs() / std > threshold
    flagged = flagged.fillna(False)

    result = df.copy()
    result[f"{column}{FLAG_SUFFIX}"] = flagged.map({True: "True", False: "False"})
    return result, int(flagged.sum())
