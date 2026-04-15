"""Tests for zxtoolbox.git_config module."""

import configparser
import os
import subprocess
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
    git_pull,
    git_pull_by_name,
    git_clone,
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


class TestGitPull:
    """Test git pull functionality."""

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_success(self, mock_find_git_dir, mock_run, capsys):
        """Test successful git pull."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Already up to date.\n", stderr=""
        )
        result = git_pull(project_dir="/fake/project")
        assert result is True
        captured = capsys.readouterr()
        assert "Already up to date" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_success_with_output(self, mock_find_git_dir, mock_run, capsys):
        """Test git pull with fetch and merge output."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Updating abc1234..def5678\nFast-forward\n",
            stderr="",
        )
        result = git_pull(project_dir="/fake/project")
        assert result is True
        captured = capsys.readouterr()
        assert "Fast-forward" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_failure(self, mock_find_git_dir, mock_run, capsys):
        """Test git pull with non-zero exit code."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: failed to pull\n"
        )
        result = git_pull(project_dir="/fake/project")
        assert result is False
        captured = capsys.readouterr()
        assert "失败" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_with_remote(self, mock_find_git_dir, mock_run, capsys):
        """Test git pull with specified remote."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.\n", stderr="")
        result = git_pull(project_dir="/fake/project", remote="origin")
        assert result is True
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "pull", "origin"]

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_with_remote_and_branch(self, mock_find_git_dir, mock_run, capsys):
        """Test git pull with remote and branch."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.\n", stderr="")
        result = git_pull(project_dir="/fake/project", remote="origin", branch="main")
        assert result is True
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "pull", "origin", "main"]

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_timeout(self, mock_find_git_dir, mock_run, capsys):
        """Test git pull timeout."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git pull", timeout=120)
        result = git_pull(project_dir="/fake/project")
        assert result is False
        captured = capsys.readouterr()
        assert "超时" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    @patch("zxtoolbox.git_config.find_git_dir")
    def test_git_pull_git_not_found(self, mock_find_git_dir, mock_run, capsys):
        """Test git pull when git is not installed."""
        mock_find_git_dir.return_value = Path("/fake/project/.git")
        mock_run.side_effect = FileNotFoundError()
        result = git_pull(project_dir="/fake/project")
        assert result is False
        captured = capsys.readouterr()
        assert "未找到 git 命令" in captured.out

    def test_git_pull_no_git_repo(self, tmp_path, capsys):
        """Test git pull in a non-git directory."""
        result = git_pull(project_dir=str(tmp_path))
        assert result is False
        captured = capsys.readouterr()
        assert "未找到 Git 仓库" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    def test_git_pull_default_cwd(self, mock_run, capsys):
        """Test git pull with default project_dir uses cwd."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.\n", stderr="")
        with patch("os.getcwd", return_value="/fake/project"):
            with patch("zxtoolbox.git_config.find_git_dir", return_value=Path("/fake/project/.git")):
                result = git_pull()
                assert result is True


class TestGitClone:
    """Test git clone functionality."""

    @patch("zxtoolbox.git_config.subprocess.run")
    def test_git_clone_success(self, mock_run, capsys):
        """Test successful git clone."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Cloning into 'repo'...\n", stderr=""
        )
        result = git_clone("https://github.com/user/repo.git", target_dir="/fake/target")
        assert result is True
        captured = capsys.readouterr()
        assert "Cloning" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    def test_git_clone_failure(self, mock_run, capsys):
        """Test git clone failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: repository not found\n"
        )
        result = git_clone("https://github.com/user/nonexistent.git", target_dir="/fake/target")
        assert result is False
        captured = capsys.readouterr()
        assert "失败" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    def test_git_clone_timeout(self, mock_run, capsys):
        """Test git clone timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git clone", timeout=300)
        result = git_clone("https://github.com/user/repo.git", target_dir="/fake/target")
        assert result is False
        captured = capsys.readouterr()
        assert "超时" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    def test_git_clone_git_not_found(self, mock_run, capsys):
        """Test git clone when git is not installed."""
        mock_run.side_effect = FileNotFoundError()
        result = git_clone("https://github.com/user/repo.git", target_dir="/fake/target")
        assert result is False
        captured = capsys.readouterr()
        assert "未找到 git 命令" in captured.out

    @patch("zxtoolbox.git_config.subprocess.run")
    def test_git_clone_without_target_dir(self, mock_run):
        """Test git clone without target directory uses cwd."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = git_clone("https://github.com/user/repo.git")
        assert result is True
        # Verify command includes repo URL but no target dir
        call_args = mock_run.call_args[0][0]
        assert "https://github.com/user/repo.git" in call_args


class TestGitPullByName:
    """Test git pull by project name functionality."""

    @patch("zxtoolbox.git_config.git_pull")
    @patch("zxtoolbox.config_manager.load_config")
    def test_pull_by_name_project_exists(self, mock_load_config, mock_pull, capsys):
        """Test git pull by name when project directory exists."""
        mock_load_config.return_value = {
            "projects": [
                {
                    "name": "myblog",
                    "project_dir": "/tmp/test-myblog",
                    "git_repository": "https://github.com/user/myblog.git",
                }
            ]
        }
        mock_pull.return_value = True

        with patch.object(Path, "exists", return_value=True):
            with patch("zxtoolbox.git_config.find_git_dir", return_value=Path("/tmp/test-myblog/.git")):
                result = git_pull_by_name("myblog")
                assert result is True

    @patch("zxtoolbox.git_config.git_clone")
    @patch("zxtoolbox.config_manager.load_config")
    def test_pull_by_name_clone_when_dir_missing(self, mock_load_config, mock_clone, capsys):
        """Test git pull by name when directory doesn't exist but git_repository is configured."""
        mock_load_config.return_value = {
            "projects": [
                {
                    "name": "myblog",
                    "project_dir": "/tmp/test-myblog-missing",
                    "git_repository": "https://github.com/user/myblog.git",
                }
            ]
        }
        mock_clone.return_value = True

        with patch.object(Path, "exists", return_value=False):
            result = git_pull_by_name("myblog")
            assert result is True
            # Verify git_clone was called with the right arguments
            mock_clone.assert_called_once()
            call_args = mock_clone.call_args
            assert call_args[1]["repository"] == "https://github.com/user/myblog.git"

    @patch("zxtoolbox.config_manager.load_config")
    def test_pull_by_name_not_found_in_config(self, mock_load_config, capsys):
        """Test git pull by name when name is not found in config."""
        mock_load_config.return_value = {"projects": []}

        result = git_pull_by_name("nonexistent")
        assert result is False
        captured = capsys.readouterr()
        assert "未在配置文件中找到" in captured.out

    @patch("zxtoolbox.config_manager.load_config")
    def test_pull_by_name_no_project_dir(self, mock_load_config, capsys):
        """Test git pull by name when project_dir is missing."""
        mock_load_config.return_value = {
            "projects": [{"name": "myblog"}]
        }

        result = git_pull_by_name("myblog")
        assert result is False
        captured = capsys.readouterr()
        assert "未配置 project_dir" in captured.out

    @patch("zxtoolbox.config_manager.load_config")
    def test_pull_by_name_dir_missing_no_git_repo(self, mock_load_config, capsys):
        """Test git pull by name when dir is missing and no git_repository configured."""
        mock_load_config.return_value = {
            "projects": [
                {
                    "name": "myblog",
                    "project_dir": "/tmp/test-myblog-no-git",
                }
            ]
        }

        with patch.object(Path, "exists", return_value=False):
            result = git_pull_by_name("myblog")
            assert result is False
            captured = capsys.readouterr()
            assert "未配置 git_repository" in captured.out

    @patch("zxtoolbox.git_config.git_pull")
    @patch("zxtoolbox.git_config.find_git_dir")
    @patch("zxtoolbox.config_manager.load_config")
    def test_pull_by_name_with_remote_and_branch(self, mock_load_config, mock_find, mock_pull, capsys):
        """Test git pull by name with remote and branch parameters."""
        mock_load_config.return_value = {
            "projects": [
                {
                    "name": "myblog",
                    "project_dir": "/tmp/test-myblog-remote",
                    "git_repository": "https://github.com/user/myblog.git",
                }
            ]
        }
        mock_find.return_value = Path("/tmp/test-myblog-remote/.git")
        mock_pull.return_value = True

        with patch.object(Path, "exists", return_value=True):
            result = git_pull_by_name("myblog", remote="origin", branch="main")
            assert result is True
            mock_pull.assert_called_once_with(
                project_dir=str(Path("/tmp/test-myblog-remote").resolve()),
                remote="origin",
                branch="main",
            )
