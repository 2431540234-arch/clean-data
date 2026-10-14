"""Che dữ liệu cá nhân (PII) trước khi gửi mẫu dữ liệu cho AI provider bên ngoài."""

from typing import Any


def mask_sample_values(sample_values: list[Any]) -> list[Any]:
    """Che một phần giá trị nhạy cảm (email, số điện thoại, họ tên) trước khi gửi cho AI.

    Gợi ý cách làm: với email giữ lại ký tự đầu + domain (vd "a***@gmail.com"); với số
    điện thoại giữ 3 số đầu + 2 số cuối; với tên giữ chữ cái đầu mỗi từ.
    """
    raise NotImplementedError("TODO: che một phần giá trị nhạy cảm trong sample_values.")
