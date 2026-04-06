"""Tests for zxtoolbox.config_manager module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from zxtoolbox.config_manager import (
    DEFAULT_CONFIG_PATH,
    _escape_toml_string,
    _generate_mkdocs_section,
    _generate_git_section,
    generate_config_content,
    write_config,
    show_config,
)


class TestEscapeTomlString:
    """Test TOML string escaping."""

    def test_simple_string(self):
        result = _escape_toml_string("hello")
        assert result == '"hello"'

    def test_string_with_quotes(self):
        result = _escape_toml_string('hello "world"')
        assert '\\"' in result

    def test_string_with_backslash(self):
        result = _escape_toml_string("path\\to\\file")
        assert "\\\\" in result

    def test_string_with_newline(self):
        result = _escape_toml_string("line1\nline2")
        assert "\\n" in result

    def test_string_with_tab(self):
        result = _escape_toml_string("col1\tcol2")
        assert "\\t" in result

    def test_empty_string(self):
        result = _escape_toml_string("")
        assert result == '""'


class TestGenerateMkdocsSection:
    """Test MkDocs config generation."""

    def test_empty_projects(self):
        result = _generate_mkdocs_section([])
        assert result == ""

    def test_single_project(self):
        projects = [{"project_dir": "/path/to/docs"}]
        result = _generate_mkdocs_section(projects)
        assert "[[projects]]" in result
        assert '"/path/to/docs"' in result

    def test_project_with_all_fields(self):
        projects = [
            {
                "project_dir": "/path/to/docs",
                "output_dir": "/output",
                "config_file": "custom.yml",
                "strict": True,
            }
        ]
        result = _generate_mkdocs_section(projects)
        assert "output_dir" in result
        assert "config_file" in result
        assert "strict = true" in result

    def test_multiple_projects(self):
        projects = [
            {"project_dir": "/path/1"},
            {"project_dir": "/path/2"},
        ]
        result = _generate_mkdocs_section(projects)
        assert result.count("[[projects]]") == 2


class TestGenerateGitSection:
    """Test Git config generation."""

    def test_empty_users(self):
        result = _generate_git_section([])
        assert result == ""

    def test_single_user(self):
        users = [{"name": "John", "email": "john@example.com"}]
        result = _generate_git_section(users)
        assert "[[git.user]]" in result
        assert '"John"' in result
        assert '"john@example.com"' in result

    def test_multiple_users(self):
        users = [
            {"name": "John", "email": "john@example.com"},
            {"name": "Jane", "email": "jane@example.com"},
        ]
        result = _generate_git_section(users)
        assert result.count("[[git.user]]") == 2

    def test_user_missing_email(self):
        users = [{"name": "John"}]
        result = _generate_git_section(users)
        assert '"John"' in result
        assert "email" not in result


class TestGenerateConfigContent:
    """Test full config content generation."""

    def test_empty_config(self):
        result = generate_config_content()
        assert "zxtool" in result
        assert "暂无配置项" in result

    def test_with_mkdocs_and_git(self):
        result = generate_config_content(
            mkdocs_projects=[{"project_dir": "/docs"}],
            git_users=[{"name": "John", "email": "john@example.com"}],
        )
        assert "[[projects]]" in result
        assert "[[git.user]]" in result
        assert "暂无配置项" not in result

    def test_header_present(self):
        result = generate_config_content()
        assert "# zxtool 全局配置文件" in result
        assert "# 路径: ~/.config/zxtool.toml" in result


class TestWriteConfig:
    """Test config file writing."""

    def test_write_new_config(self, tmp_path):
        """Test writing a new config file."""
        config_path = tmp_path / "zxtool.toml"
        result = write_config(
            config_path,
            mkdocs_projects=[{"project_dir": "/docs"}],
            git_users=[{"name": "John", "email": "john@example.com"}],
            force=True,
        )
        assert result is True
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "[[projects]]" in content
        assert "[[git.user]]" in content

    def test_write_existing_config_without_force(self, tmp_path):
        """Test writing to existing file without force."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text("existing")

        result = write_config(config_path, force=False)

        assert result is False

    def test_write_existing_config_with_force(self, tmp_path):
        """Test overwriting existing file with force."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text("existing")

        result = write_config(
            config_path,
            mkdocs_projects=[{"project_dir": "/docs"}],
            force=True,
        )

        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert "existing" not in content

    def test_write_creates_parent_dir(self, tmp_path):
        """Test that parent directories are created."""
        config_path = tmp_path / "subdir" / "zxtool.toml"
        result = write_config(config_path, force=True)
        assert result is True
        assert config_path.exists()

    def test_write_empty_config(self, tmp_path):
        """Test writing an empty config."""
        config_path = tmp_path / "zxtool.toml"
        result = write_config(config_path, force=True)
        assert result is True
        content = config_path.read_text(encoding="utf-8")
        assert "暂无配置项" in content


class TestShowConfig:
    """Test config file display."""

    def test_show_existing_config(self, tmp_path, capsys):
        """Test showing an existing config file."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('# Test config\n[[projects]]\nproject_dir = "/docs"\n')

        show_config(str(config_path))

        captured = capsys.readouterr()
        assert "# Test config" in captured.out
        assert "[[projects]]" in captured.out

    def test_show_missing_config(self, tmp_path, capsys):
        """Test showing a non-existent config file."""
        config_path = tmp_path / "nonexistent.toml"

        show_config(str(config_path))

        captured = capsys.readouterr()
        assert "不存在" in captured.out


class TestInteractiveInit:
    """Test interactive config initialization."""

    @patch("builtins.input", side_effect=["", "", EOFError()])
    def test_interactive_init_skip_all(self, mock_input, tmp_path):
        """Test interactive init with no input (skipping all sections)."""
        config_path = tmp_path / "zxtool.toml"
        # This will hit EOFError when asking for confirmation
        # which should return False gracefully
        from zxtoolbox.config_manager import interactive_init

        result = interactive_init(config_path)
        # Should return False due to EOFError/cancel
        assert result is False
