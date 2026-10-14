"""Cấu hình logging chung cho backend."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Khởi tạo logging ra stdout với format đơn giản, gọi một lần khi app start."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """Lấy logger theo tên module, ví dụ ``get_logger(__name__)``."""
    return logging.getLogger(name)
