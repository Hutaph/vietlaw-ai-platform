"""
Centralized backend logging configuration.
Use this helper instead of print() so logs keep a consistent format.
"""
import logging
import sys


def setup_logger(name: str = "vietlaw") -> logging.Logger:
    """Create a logger with the standard VietLaw format."""
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


# Default application logger.
logger = setup_logger()
