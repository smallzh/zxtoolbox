"""Logging setup for zxtoolbox."""

from __future__ import annotations

import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from zxtoolbox.config_manager import load_logging_config


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_BACKUP_COUNT = 7

_initialized = False


def _get_log_file_path(log_dir: str) -> Path:
    """Return the current day log file path and ensure directory exists."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return log_path / f"zxtool_{today}.log"


def setup_logging(config_path: str | Path | None = None) -> logging.FileHandler | None:
    """Initialize package logging from config or safe defaults."""
    global _initialized

    if _initialized:
        return None

    try:
        log_config = load_logging_config(config_path)
    except (FileNotFoundError, PermissionError, OSError):
        log_config = {
            "log_dir": str(Path.home() / ".config" / "zxtool_logs"),
            "log_level": "INFO",
        }

    log_dir = log_config.get("log_dir", str(Path.home() / ".config" / "zxtool_logs"))
    log_level_str = str(log_config.get("log_level", "INFO")).upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = level_map.get(log_level_str, logging.INFO)

    try:
        log_file = _get_log_file_path(log_dir)
    except OSError:
        return None

    try:
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.suffix = "%Y-%m-%d.log"
        file_handler.setLevel(log_level)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        file_handler.setFormatter(formatter)

        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.setLevel(log_level)
        pkg_logger.addHandler(file_handler)

        _initialized = True
        return file_handler
    except OSError:
        return None


def reset_logging() -> None:
    """Reset logging state for tests."""
    global _initialized
    _initialized = False

    pkg_logger = logging.getLogger("zxtoolbox")
    for handler in pkg_logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        pkg_logger.removeHandler(handler)
    pkg_logger.setLevel(logging.WARNING)
