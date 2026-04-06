"""Tests for zxtoolbox.cli module."""

import sys
from unittest.mock import patch

import pytest

from zxtoolbox import cli


class TestCliMain:
    """Test CLI main function dispatch."""

    def test_main_no_args_shows_help(self, capsys):
        """Test that running without arguments shows help."""
        with patch.object(sys, "argv", ["zxtool"]):
            cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "zxtool" in captured.out.lower()

    def test_main_help_shows_help(self, capsys):
        """Test that --help shows help."""
        with patch.object(sys, "argv", ["zxtool", "--help"]):
            with pytest.raises(SystemExit):
                cli.main()
        captured = capsys.readouterr()
        assert "zxtool" in captured.out.lower() or "usage" in captured.out.lower()


class TestCliComputer:
    """Test CLI computer info commands."""

    @patch("zxtoolbox.computer_info.get_all_info")
    def test_computer_default(self, mock_get_all, capsys):
        """Test default computer info command."""
        with patch.object(sys, "argv", ["zxtool", "-c"]):
            cli.main()
        mock_get_all.assert_called_once()

    @patch("zxtoolbox.computer_info.summary_info")
    def test_computer_short(self, mock_summary, capsys):
        """Test short computer info command."""
        with patch.object(sys, "argv", ["zxtool", "-c", "-s"]):
            cli.main()
        mock_summary.assert_called_once()

    @patch("zxtoolbox.computer_info.detailed_info")
    def test_computer_all(self, mock_detailed, capsys):
        """Test detailed computer info command."""
        with patch.object(sys, "argv", ["zxtool", "-c", "-a"]):
            cli.main()
        mock_detailed.assert_called_once()


class TestCliTotp:
    """Test CLI TOTP commands."""

    @patch("zxtoolbox.pyopt_2fa.parseTotpCdoe")
    def test_totp_with_key(self, mock_parse, capsys):
        """Test TOTP with key."""
        with patch.object(sys, "argv", ["zxtool", "-t", "-k", "TESTKEY"]):
            cli.main()
        mock_parse.assert_called_once_with("TESTKEY")

    def test_totp_without_key(self, capsys):
        """Test TOTP without key shows error."""
        with patch.object(sys, "argv", ["zxtool", "-t"]):
            cli.main()
        captured = capsys.readouterr()
        assert "Error" in captured.out or "required" in captured.out


class TestCliVideo:
    """Test CLI video download commands."""

    @patch("zxtoolbox.video_download.download_with_progress")
    def test_video_with_url(self, mock_download, capsys):
        """Test video download with URL."""
        with patch.object(sys, "argv", ["zxtool", "-v", "-u", "https://example.com"]):
            cli.main()
        mock_download.assert_called_once_with("https://example.com", None)

    def test_video_without_url(self, capsys):
        """Test video download without URL shows error."""
        with patch.object(sys, "argv", ["zxtool", "-v"]):
            cli.main()
        captured = capsys.readouterr()
        assert "Error" in captured.out or "required" in captured.out


class TestCliGit:
    """Test CLI git subcommand."""

    def test_git_no_subcommand_shows_help(self, capsys):
        """Test git without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "git"]):
            cli.main()
        captured = capsys.readouterr()
        assert "git" in captured.out.lower()

    def test_git_config_no_subcommand_shows_help(self, capsys):
        """Test git config without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "git", "config"]):
            cli.main()
        captured = capsys.readouterr()
        assert "config" in captured.out.lower()

    @patch("zxtoolbox.git_config.check_git_config")
    def test_git_config_check(self, mock_check, capsys):
        """Test git config check command."""
        mock_check.return_value = {"name": "Test", "email": "test@test.com"}
        with patch.object(sys, "argv", ["zxtool", "git", "config", "check"]):
            cli.main()
        mock_check.assert_called_once_with(None)
        captured = capsys.readouterr()
        assert "Test" in captured.out

    @patch("zxtoolbox.git_config.fill_git_config")
    def test_git_config_fill(self, mock_fill, capsys):
        """Test git config fill command."""
        with patch.object(
            sys,
            "argv",
            [
                "zxtool",
                "git",
                "config",
                "fill",
                "--name",
                "Test",
                "--email",
                "test@test.com",
            ],
        ):
            cli.main()
        mock_fill.assert_called_once_with(
            project_dir=None, config_file=None, name="Test", email="test@test.com"
        )

    @patch("zxtoolbox.git_config.check_git_config")
    def test_git_config_check_with_project(self, mock_check, capsys):
        """Test git config check with project directory."""
        mock_check.return_value = None
        with patch.object(
            sys, "argv", ["zxtool", "git", "config", "check", "/path/to/project"]
        ):
            cli.main()
        mock_check.assert_called_once_with("/path/to/project")


class TestCliConfig:
    """Test CLI config subcommand."""

    def test_config_no_subcommand_shows_help(self, capsys):
        """Test config without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "config"]):
            cli.main()
        captured = capsys.readouterr()
        assert "config" in captured.out.lower()

    @patch("zxtoolbox.config_manager.interactive_init")
    def test_config_init(self, mock_init, capsys):
        """Test config init command."""
        with patch.object(sys, "argv", ["zxtool", "config", "init"]):
            cli.main()
        mock_init.assert_called_once_with(config_path=None, force=False)

    @patch("zxtoolbox.config_manager.interactive_init")
    def test_config_init_with_options(self, mock_init, capsys):
        """Test config init with options."""
        with patch.object(
            sys,
            "argv",
            ["zxtool", "config", "init", "--path", "/custom/path", "--force"],
        ):
            cli.main()
        mock_init.assert_called_once_with(config_path="/custom/path", force=True)

    @patch("zxtoolbox.config_manager.show_config")
    def test_config_show(self, mock_show, capsys):
        """Test config show command."""
        with patch.object(sys, "argv", ["zxtool", "config", "show"]):
            cli.main()
        mock_show.assert_called_once_with(config_path=None)

    @patch("zxtoolbox.config_manager.show_config")
    def test_config_show_with_path(self, mock_show, capsys):
        """Test config show with custom path."""
        with patch.object(
            sys, "argv", ["zxtool", "config", "show", "--path", "/custom/config.toml"]
        ):
            cli.main()
        mock_show.assert_called_once_with(config_path="/custom/config.toml")


class TestCliMkdocs:
    """Test CLI mkdocs subcommand."""

    def test_mkdocs_no_subcommand_shows_help(self, capsys):
        """Test mkdocs without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "mkdocs"]):
            cli.main()
        captured = capsys.readouterr()
        assert "mkdocs" in captured.out.lower()

    @patch("zxtoolbox.mkdocs_manager.create_project")
    def test_mkdocs_create(self, mock_create, capsys):
        """Test mkdocs create command."""
        with patch.object(
            sys,
            "argv",
            ["zxtool", "mkdocs", "create", "/path/to/project", "--name", "My Site"],
        ):
            cli.main()
        mock_create.assert_called_once_with("/path/to/project", site_name="My Site")

    @patch("zxtoolbox.mkdocs_manager.build_project")
    def test_mkdocs_build(self, mock_build, capsys):
        """Test mkdocs build command."""
        with patch.object(
            sys,
            "argv",
            [
                "zxtool",
                "mkdocs",
                "build",
                "/path/to/project",
                "-o",
                "/output",
                "--strict",
            ],
        ):
            cli.main()
        mock_build.assert_called_once_with(
            project_dir="/path/to/project",
            output_dir="/output",
            config_file=None,
            strict=True,
        )

    @patch("zxtoolbox.mkdocs_manager.batch_build")
    def test_mkdocs_batch(self, mock_batch, capsys):
        """Test mkdocs batch command."""
        with patch.object(
            sys, "argv", ["zxtool", "mkdocs", "batch", "/config.toml", "--dry-run"]
        ):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path="/config.toml",
            dry_run=True,
        )
