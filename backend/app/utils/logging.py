"""
Cấu hình logging chuẩn cho toàn bộ backend.
Thay thế tất cả print() bằng logger có format thống nhất.
"""
import logging
import sys


def setup_logger(name: str = "vietlaw") -> logging.Logger:
    """Tạo logger với format tiếng Việt dễ đọc."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


# Logger mặc định cho toàn hệ thống
logger = setup_logger()
