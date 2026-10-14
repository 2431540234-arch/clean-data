"""Registry pattern cho các op của Rule Engine.

Mỗi op được đăng ký bằng decorator ``@register("ten_op")`` và phải có chữ ký:
    (df: pd.DataFrame, column: str | None, params: dict) -> tuple[pd.DataFrame, int]

``OPS`` là bảng tra cứu tên op -> hàm thực thi, dùng bởi ``app.services.rules.engine``.
Import các module trong ``app.services.rules.ops`` sẽ tự đăng ký op vào registry này.
"""

from collections.abc import Callable
from typing import Any

import pandas as pd

RuleOpFunc = Callable[[pd.DataFrame, "str | None", dict[str, Any]], tuple[pd.DataFrame, int]]

OPS: dict[str, RuleOpFunc] = {}


def register(op_name: str) -> Callable[[RuleOpFunc], RuleOpFunc]:
    """Decorator đăng ký một hàm op vào registry với tên ``op_name``.

    Raises:
        ValueError: nếu ``op_name`` đã được đăng ký trước đó (tránh ghi đè nhầm).
    """

    def decorator(func: RuleOpFunc) -> RuleOpFunc:
        if op_name in OPS:
            raise ValueError(f"Op '{op_name}' đã được đăng ký trước đó.")
        OPS[op_name] = func
        return func

    return decorator


def get_op(op_name: str) -> RuleOpFunc:
    """Lấy hàm thực thi của một op theo tên.

    Raises:
        KeyError: nếu op_name chưa được đăng ký trong registry.
    """
    if op_name not in OPS:
        raise KeyError(f"Op '{op_name}' chưa được đăng ký trong Rule Engine.")
    return OPS[op_name]
