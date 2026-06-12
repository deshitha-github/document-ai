"""Logging utility module."""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

def get_logger(name):
    """Initialize and return a logger with file and console handlers."""
    # Ensure 'logs/' exists
    os.makedirs("logs", exist_ok=True)

    # Common log format
    fmt = "%(asctime)s - %(name)s - Line: %(lineno)d - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)

    # File handler (rotates at 10 MB, keeps 5 backups) with UTF-8 encoding
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"  # Enables Unicode
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Ensure stdout can handle UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Enables Unicode in console
    except AttributeError:
        # Fallback for older Python versions
        pass

    # Stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    # Logger setup
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid adding duplicate handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger
