"""Tests for zxtoolbox.logging_manager module."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from zxtoolbox.logging_manager import setup_logging, reset_logging


@pytest.fixture(autouse=True)
def _reset_logging():
    """每个测试前后重置日志状态，避免测试间干扰。"""
    reset_logging()
    yield
    reset_logging()


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_with_config(self, tmp_path):
        """Test setup_logging reads from config file."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "INFO"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None
        assert isinstance(handler, logging.FileHandler)
        assert handler.level == logging.INFO

        # 验证日志目录和文件已创建
        assert log_dir.exists()

        # 清理 handler
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.removeHandler(handler)
        handler.close()

    def test_setup_logging_default_when_no_config(self, tmp_path):
        """Test setup_logging uses defaults when config file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.toml"
        handler = setup_logging(config_path=str(nonexistent))
        assert handler is not None
        assert isinstance(handler, logging.FileHandler)
        assert handler.level == logging.INFO

        # 清理
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.removeHandler(handler)
        handler.close()

    def test_setup_logging_debug_level(self, tmp_path):
        """Test setup_logging with DEBUG level."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "DEBUG"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None
        assert handler.level == logging.DEBUG

        # 清理
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.removeHandler(handler)
        handler.close()

    def test_setup_logging_writes_to_file(self, tmp_path):
        """Test that logging actually writes to the log file."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "INFO"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None

        # 写入日志
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.info("test log message")

        # 刷新 handler 确保写入
        handler.flush()

        # 验证日志文件中有内容
        log_files = list(log_dir.glob("zxtool_*.log"))
        assert len(log_files) >= 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "test log message" in content

        # 清理
        pkg_logger.removeHandler(handler)
        handler.close()

    def test_setup_logging_no_duplicate_init(self, tmp_path):
        """Test that calling setup_logging twice doesn't create duplicate handlers."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "INFO"
''', encoding="utf-8")

        handler1 = setup_logging(config_path=str(config_path))
        handler2 = setup_logging(config_path=str(config_path))

        assert handler1 is not None
        assert handler2 is None  # Second call should return None

        # Only one handler should be added
        pkg_logger = logging.getLogger("zxtoolbox")
        file_handlers = [h for h in pkg_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

        # 清理
        pkg_logger.removeHandler(handler1)
        handler1.close()

    def test_setup_logging_error_level(self, tmp_path):
        """Test setup_logging with ERROR level."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "ERROR"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None
        assert handler.level == logging.ERROR

        # 清理
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.removeHandler(handler)
        handler.close()

    def test_setup_logging_warning_level(self, tmp_path):
        """Test setup_logging with WARNING level."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "WARNING"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None
        assert handler.level == logging.WARNING

        # 清理
        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.removeHandler(handler)
        handler.close()

    def test_info_log_not_written_when_error_level(self, tmp_path):
        """Test that INFO messages are not written when log level is ERROR."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "ERROR"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None

        pkg_logger = logging.getLogger("zxtoolbox")
        pkg_logger.info("this info should not appear")
        pkg_logger.error("this error should appear")

        handler.flush()

        log_files = list(log_dir.glob("zxtool_*.log"))
        assert len(log_files) >= 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "this info should not appear" not in content
        assert "this error should appear" in content

        # 清理
        pkg_logger.removeHandler(handler)
        handler.close()


class TestResetLogging:
    """Test reset_logging function."""

    def test_reset_clears_handlers(self, tmp_path):
        """Test that reset_logging clears all handlers."""
        config_path = tmp_path / "zxtool.toml"
        log_dir = tmp_path / "logs"
        config_path.write_text(f'''
[logging]
log_dir = "{str(log_dir).replace("\\", "\\\\")}"
log_level = "INFO"
''', encoding="utf-8")

        handler = setup_logging(config_path=str(config_path))
        assert handler is not None

        pkg_logger = logging.getLogger("zxtoolbox")
        assert len(pkg_logger.handlers) > 0

        reset_logging()
        assert len(pkg_logger.handlers) == 0

        # 清理
        handler.close()
