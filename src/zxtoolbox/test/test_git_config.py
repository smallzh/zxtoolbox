"""Tests for zxtoolbox.git_config module."""

import configparser
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from zxtoolbox.git_config import (
    find_git_dir,
    read_git_config,
    get_user_info,
    set_user_info,
    write_git_config,
    load_zxtool_config,
    check_git_config,
    fill_git_config,
)


class TestFindGitDir:
    """Test .git directory discovery."""

    def test_find_git_dir_current(self, tmp_path):
        """Test finding .git in the given directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        result = find_git_dir(str(tmp_path))
        assert result == git_dir

    def test_find_git_dir_subdir(self, tmp_path):
        """Test finding .git from a subdirectory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        subdir = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)
        result = find_git_dir(str(subdir))
        assert result == git_dir

    def test_find_git_dir_not_found(self, tmp_path):
        """Test when no .git directory exists."""
        result = find_git_dir(str(tmp_path))
        assert result is None

    @patch("os.getcwd")
    def test_find_git_dir_default_cwd(self, mock_cwd, tmp_path):
        """Test default uses current working directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_cwd.return_value = str(tmp_path)
        result = find_git_dir()
        assert result == git_dir


class TestReadGitConfig:
    """Test reading .git/config files."""

    def test_read_existing_config(self, tmp_path):
        """Test reading an existing config file."""
        config_file = tmp_path / "config"
        config_file.write_text("[user]\nname = Test\nemail = test@test.com\n")
        result = read_git_config(tmp_path)
        assert result is not None
        assert result.get("user", "name") == "Test"

    def test_read_missing_config(self, tmp_path):
        """Test reading a non-existent config file."""
        result = read_git_config(tmp_path)
        assert result is None


class TestGetUserInfo:
    """Test extracting user info from config."""

    def test_get_user_info_complete(self):
        config = configparser.ConfigParser()
        config.add_section("user")
        config.set("user", "name", "John")
        config.set("user", "email", "john@example.com")
        result = get_user_info(config)
        assert result == {"name": "John", "email": "john@example.com"}

    def test_get_user_info_missing(self):
        config = configparser.ConfigParser()
        result = get_user_info(config)
        assert result == {"name": "", "email": ""}

    def test_get_user_info_partial(self):
        config = configparser.ConfigParser()
        config.add_section("user")
        config.set("user", "name", "John")
        result = get_user_info(config)
        assert result["name"] == "John"
        assert result["email"] == ""


class TestSetUserInfo:
    """Test setting user info in config."""

    def test_set_user_info_new_section(self):
        config = configparser.ConfigParser()
        set_user_info(config, "John", "john@example.com")
        assert config.get("user", "name") == "John"
        assert config.get("user", "email") == "john@example.com"

    def test_set_user_info_existing_section(self):
        config = configparser.ConfigParser()
        config.add_section("user")
        config.set("user", "name", "Old")
        set_user_info(config, "New", "new@example.com")
        assert config.get("user", "name") == "New"
        assert config.get("user", "email") == "new@example.com"


class TestWriteGitConfig:
    """Test writing .git/config files."""

    def test_write_git_config(self, tmp_path):
        """Test writing config to file."""
        config = configparser.ConfigParser()
        config.add_section("user")
        config.set("user", "name", "Test")
        config.set("user", "email", "test@test.com")

        write_git_config(tmp_path, config)

        config_file = tmp_path / "config"
        assert config_file.exists()
        content = config_file.read_text()
        assert "Test" in content
        assert "test@test.com" in content


class TestLoadZxtoolConfig:
    """Test loading zxtool.toml configuration."""

    def test_load_missing_config(self):
        """Test loading a non-existent config file."""
        result = load_zxtool_config("/nonexistent/path/zxtool.toml")
        assert result == []

    def test_load_config_with_git_users(self, tmp_path):
        """Test loading config with git.user entries."""
        config_file = tmp_path / "zxtool.toml"
        config_file.write_text(
            '[[git.user]]\nname = "John"\nemail = "john@example.com"\n'
            '[[git.user]]\nname = "Jane"\nemail = "jane@example.com"\n'
        )
        result = load_zxtool_config(str(config_file))
        assert len(result) == 2
        assert result[0] == {"name": "John", "email": "john@example.com"}
        assert result[1] == {"name": "Jane", "email": "jane@example.com"}

    def test_load_config_no_git_section(self, tmp_path):
        """Test loading config without git section."""
        config_file = tmp_path / "zxtool.toml"
        config_file.write_text('[[projects]]\nproject_dir = "/path"\n')
        result = load_zxtool_config(str(config_file))
        assert result == []

    def test_load_config_empty_git_user(self, tmp_path):
        """Test loading config with empty git.user list."""
        config_file = tmp_path / "zxtool.toml"
        config_file.write_text("[git]\nuser = []\n")
        result = load_zxtool_config(str(config_file))
        assert result == []


class TestCheckGitConfig:
    """Test checking git user configuration."""

    def test_check_config_complete(self, tmp_path):
        """Test checking a repo with complete user config."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = git_dir / "config"
        config_file.write_text("[user]\nname = John\nemail = john@example.com\n")
        result = check_git_config(str(tmp_path))
        assert result == {"name": "John", "email": "john@example.com"}

    def test_check_config_incomplete(self, tmp_path):
        """Test checking a repo with partial user config."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = git_dir / "config"
        config_file.write_text("[user]\nname = John\n")
        result = check_git_config(str(tmp_path))
        assert result is None

    def test_check_config_no_user(self, tmp_path):
        """Test checking a repo without user section."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = git_dir / "config"
        config_file.write_text("[core]\nrepositoryformatversion = 0\n")
        result = check_git_config(str(tmp_path))
        assert result is None

    def test_check_config_no_repo(self, tmp_path):
        """Test checking a non-git directory."""
        result = check_git_config(str(tmp_path))
        assert result is None


class TestFillGitConfig:
    """Test filling git user configuration."""

    def test_fill_config_with_args(self, tmp_path, capsys):
        """Test filling config with command-line arguments."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = git_dir / "config"
        config_file.write_text("[core]\nrepositoryformatversion = 0\n")

        result = fill_git_config(
            str(tmp_path), name="TestUser", email="test@example.com"
        )

        assert result is True
        # Verify config was written
        config = configparser.ConfigParser()
        config.read(str(config_file))
        assert config.get("user", "name") == "TestUser"
        assert config.get("user", "email") == "test@example.com"

    def test_fill_config_already_complete(self, tmp_path, capsys):
        """Test filling config when already configured."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = git_dir / "config"
        config_file.write_text("[user]\nname = Existing\nemail = existing@test.com\n")

        result = fill_git_config(str(tmp_path))

        assert result is True
        captured = capsys.readouterr()
        assert "Existing" in captured.out

    def test_fill_config_no_repo(self, tmp_path):
        """Test filling config in a non-git directory."""
        result = fill_git_config(str(tmp_path))
        assert result is False

    def test_fill_config_from_zxtool_toml(self, tmp_path, capsys):
        """Test filling config from zxtool.toml."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        config_file = git_dir / "config"
        config_file.write_text("[core]\nrepositoryformatversion = 0\n")

        zxtool_config = tmp_path / "zxtool.toml"
        zxtool_config.write_text(
            '[[git.user]]\nname = "ConfigUser"\nemail = "config@test.com"\n'
        )

        result = fill_git_config(str(tmp_path), config_file=str(zxtool_config))

        assert result is True
        config = configparser.ConfigParser()
        config.read(str(config_file))
        assert config.get("user", "name") == "ConfigUser"
        assert config.get("user", "email") == "config@test.com"
