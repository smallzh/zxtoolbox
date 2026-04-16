"""zxtool 日志管理模块。

根据 zxtool.toml 中的 [logging] 配置，初始化全局日志系统。
日志级别 INFO 及以上的消息将输出到配置的日志文件中。

配置文件结构::

    [logging]
    log_dir = "/path/to/logs"
    log_level = "INFO"

默认日志目录为 ~/.config/zxtool_logs，默认日志级别为 INFO。
日志文件按日期轮转，保留最近 7 天的日志。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from zxtoolbox.config_manager import DEFAULT_CONFIG_PATH, load_logging_config


# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 默认日志保留天数
LOG_BACKUP_COUNT = 7

# 模块级标记，避免重复初始化
_initialized = False


def _get_log_file_path(log_dir: str) -> Path:
    """获取日志文件路径。

    日志文件名格式: zxtool_YYYY-MM-DD.log

    Args:
        log_dir: 日志目录路径。

    Returns:
        日志文件完整路径。
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    return log_path / f"zxtool_{today}.log"


def setup_logging(config_path: str | Path | None = None) -> logging.FileHandler | None:
    """根据 zxtool.toml 配置初始化全局日志系统。

    从配置文件的 [logging] 节读取 log_dir 和 log_level，
    配置根日志记录器将 INFO 及以上级别的日志输出到文件。
    同时保留控制台输出（不修改控制台行为）。

    如果配置文件不存在或 [logging] 节未配置，则使用默认值。

    Args:
        config_path: zxtool.toml 配置文件路径，默认为 ~/.config/zxtool.toml。

    Returns:
        配置好的 FileHandler 实例，如果初始化失败则返回 None。
    """
    global _initialized

    if _initialized:
        return None

    # 读取日志配置
    try:
        log_config = load_logging_config(config_path)
    except FileNotFoundError:
        # 配置文件不存在时使用默认值
        log_config = {
            "log_dir": str(Path.home() / ".config" / "zxtool_logs"),
            "log_level": "INFO",
        }

    log_dir = log_config.get("log_dir", str(Path.home() / ".config" / "zxtool_logs"))
    log_level_str = log_config.get("log_level", "INFO").upper()

    # 解析日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = level_map.get(log_level_str, logging.INFO)

    # 确保日志目录存在
    try:
        log_file = _get_log_file_path(log_dir)
    except OSError:
        return None

    # 创建文件 Handler
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

        # 配置 zxtoolbox 根日志记录器
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.setLevel(log_level)
        pkg_logger.addHandler(file_handler)

        _initialized = True
        return file_handler

    except OSError:
        return None


def reset_logging() -> None:
    """重置日志初始化状态（仅用于测试）。"""
    global _initialized
    _initialized = False

    pkg_logger = logging.getLogger("zxtoolbox")
    pkg_logger.handlers.clear()
    pkg_logger.setLevel(logging.WARNING)
