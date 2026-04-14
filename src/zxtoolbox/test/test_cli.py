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
    """Test CLI ci subcommand."""

    @patch("zxtoolbox.computer_info.summary_info")
    def test_ci_default_shows_summary(self, mock_summary, capsys):
        """Test default ci command shows summary info."""
        with patch.object(sys, "argv", ["zxtool", "ci"]):
            cli.main()
        mock_summary.assert_called_once()

    @patch("zxtoolbox.computer_info.detailed_info")
    def test_ci_all_shows_detailed(self, mock_detailed, capsys):
        """Test ci --all shows detailed info."""
        with patch.object(sys, "argv", ["zxtool", "ci", "--all"]):
            cli.main()
        mock_detailed.assert_called_once()


class TestCliTotp:
    """Test CLI totp subcommand."""

    @patch("zxtoolbox.pyopt_2fa.parseTotpCdoe")
    def test_totp_with_key(self, mock_parse, capsys):
        """Test totp with key."""
        with patch.object(sys, "argv", ["zxtool", "totp", "-k", "TESTKEY"]):
            cli.main()
        mock_parse.assert_called_once_with("TESTKEY")

    def test_totp_without_key_shows_error(self, capsys):
        """Test totp without key shows error."""
        with patch.object(sys, "argv", ["zxtool", "totp"]):
            with pytest.raises(SystemExit):
                cli.main()


class TestCliVideo:
    """Test CLI video subcommand."""

    @patch("zxtoolbox.video_download.download_with_progress")
    def test_video_with_url(self, mock_download, capsys):
        """Test video download with URL."""
        with patch.object(sys, "argv", ["zxtool", "video", "-u", "https://example.com"]):
            cli.main()
        mock_download.assert_called_once_with("https://example.com", None)

    @patch("zxtoolbox.video_download.download_with_progress")
    def test_video_with_url_and_output(self, mock_download, capsys):
        """Test video download with URL and output path."""
        with patch.object(
            sys, "argv",
            ["zxtool", "video", "-u", "https://example.com", "-o", "/tmp/vid.mp4"]
        ):
            cli.main()
        mock_download.assert_called_once_with("https://example.com", "/tmp/vid.mp4")

    def test_video_without_url_shows_error(self, capsys):
        """Test video without URL shows error."""
        with patch.object(sys, "argv", ["zxtool", "video"]):
            with pytest.raises(SystemExit):
                cli.main()


class TestCliSsl:
    """Test CLI ssl subcommand."""

    def test_ssl_no_subcommand_shows_help(self, capsys):
        """Test ssl without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "ssl"]):
            cli.main()
        captured = capsys.readouterr()
        assert "ssl" in captured.out.lower()

    @patch("zxtoolbox.ssl_cert.init")
    def test_ssl_init(self, mock_init, capsys):
        """Test ssl init command."""
        with patch.object(sys, "argv", ["zxtool", "ssl", "init"]):
            cli.main()
        mock_init.assert_called_once()

    @patch("zxtoolbox.ssl_cert.generate_root")
    def test_ssl_root(self, mock_root, capsys):
        """Test ssl root command."""
        with patch.object(sys, "argv", ["zxtool", "ssl", "root"]):
            cli.main()
        mock_root.assert_called_once()

    @patch("zxtoolbox.ssl_cert.generate_cert")
    def test_ssl_cert(self, mock_cert, capsys):
        """Test ssl cert command."""
        with patch.object(
            sys, "argv", ["zxtool", "ssl", "cert", "-d", "example.dev"]
        ):
            cli.main()
        mock_cert.assert_called_once()


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

    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_default(self, mock_pull, capsys):
        """Test git pull with default options."""
        mock_pull.return_value = True
        with patch.object(sys, "argv", ["zxtool", "git", "pull"]):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir=None, remote=None, branch=None
        )

    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_project_dir(self, mock_pull, capsys):
        """Test git pull with project directory."""
        mock_pull.return_value = True
        with patch.object(
            sys, "argv", ["zxtool", "git", "pull", "/path/to/project"]
        ):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir="/path/to/project", remote=None, branch=None
        )

    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_remote(self, mock_pull, capsys):
        """Test git pull with remote."""
        mock_pull.return_value = True
        with patch.object(
            sys, "argv", ["zxtool", "git", "pull", "--remote", "origin"]
        ):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir=None, remote="origin", branch=None
        )

    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_remote_and_branch(self, mock_pull, capsys):
        """Test git pull with remote and branch."""
        mock_pull.return_value = True
        with patch.object(
            sys, "argv",
            ["zxtool", "git", "pull", "--remote", "upstream", "--branch", "main"]
        ):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir=None, remote="upstream", branch="main"
        )

    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_project_dir_and_remote(self, mock_pull, capsys):
        """Test git pull with project dir, remote and branch."""
        mock_pull.return_value = True
        with patch.object(
            sys, "argv",
            ["zxtool", "git", "pull", "/my/project", "--remote", "origin", "--branch", "dev"]
        ):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir="/my/project", remote="origin", branch="dev"
        )


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

    @patch("zxtoolbox.mkdocs_manager.serve_project")
    def test_mkdocs_serve(self, mock_serve, capsys):
        """Test mkdocs serve command."""
        with patch.object(
            sys,
            "argv",
            ["zxtool", "mkdocs", "serve", "/path/to/project"],
        ):
            cli.main()
        mock_serve.assert_called_once_with(
            project_dir="/path/to/project",
            dev_addr=None,
            config_file=None,
            no_livereload=False,
        )

    @patch("zxtoolbox.mkdocs_manager.serve_project")
    def test_mkdocs_serve_with_options(self, mock_serve, capsys):
        """Test mkdocs serve command with dev-addr and no-livereload."""
        with patch.object(
            sys,
            "argv",
            [
                "zxtool",
                "mkdocs",
                "serve",
                "/path/to/project",
                "-a",
                "0.0.0.0:8080",
                "--no-livereload",
            ],
        ):
            cli.main()
        mock_serve.assert_called_once_with(
            project_dir="/path/to/project",
            dev_addr="0.0.0.0:8080",
            config_file=None,
            no_livereload=True,
        )


class TestCliNginx:
    """Test CLI nginx subcommand."""

    def test_nginx_no_subcommand_shows_help(self, capsys):
        """Test nginx without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "nginx"]):
            cli.main()
        captured = capsys.readouterr()
        assert "nginx" in captured.out.lower()

    @patch("zxtoolbox.nginx_manager.check_nginx")
    def test_nginx_check(self, mock_check, capsys):
        """Test nginx check command."""
        mock_check.return_value = {
            "available": True,
            "version": "nginx/1.24.0",
            "nginx_path": "/usr/sbin/nginx",
            "config_dir": "/etc/nginx",
            "sites_available": "/etc/nginx/sites-available",
            "sites_enabled": "/etc/nginx/sites-enabled",
            "conf_d": "/etc/nginx/conf.d",
        }
        with patch.object(sys, "argv", ["zxtool", "nginx", "check"]):
            cli.main()
        mock_check.assert_called_once()
        captured = capsys.readouterr()
        assert "1.24.0" in captured.out

    @patch("zxtoolbox.nginx_manager.generate_from_config")
    def test_nginx_generate(self, mock_generate, capsys):
        """Test nginx generate command."""
        mock_generate.return_value = {"example.com": "server { listen 80; }"}

        with patch.object(
            sys,
            "argv",
            ["zxtool", "nginx", "generate", "--config", "/path/to/zxtool.toml"],
        ):
            cli.main()
        mock_generate.assert_called_once_with(
            config_path="/path/to/zxtool.toml",
            output_dir=None,
            dry_run=False,
        )

    @patch("zxtoolbox.nginx_manager.generate_from_config")
    def test_nginx_generate_dry_run(self, mock_generate, capsys):
        """Test nginx generate command with dry-run."""
        mock_generate.return_value = {}

        with patch.object(
            sys,
            "argv",
            ["zxtool", "nginx", "generate", "--dry-run"],
        ):
            cli.main()
        mock_generate.assert_called_once_with(
            config_path=None,
            output_dir=None,
            dry_run=True,
        )

    @patch("zxtoolbox.nginx_manager.enable_site")
    def test_nginx_enable(self, mock_enable, capsys):
        """Test nginx enable command."""
        mock_enable.return_value = True

        with patch.object(
            sys, "argv", ["zxtool", "nginx", "enable", "example.com"]
        ):
            cli.main()
        mock_enable.assert_called_once_with("example.com")

    @patch("zxtoolbox.nginx_manager.disable_site")
    def test_nginx_disable(self, mock_disable, capsys):
        """Test nginx disable command."""
        mock_disable.return_value = True

        with patch.object(
            sys, "argv", ["zxtool", "nginx", "disable", "example.com"]
        ):
            cli.main()
        mock_disable.assert_called_once_with("example.com")

    @patch("zxtoolbox.nginx_manager.reload_nginx")
    def test_nginx_reload(self, mock_reload, capsys):
        """Test nginx reload command."""
        mock_reload.return_value = True

        with patch.object(sys, "argv", ["zxtool", "nginx", "reload"]):
            cli.main()
        mock_reload.assert_called_once()


class TestCliLetsEncrypt:
    """Test CLI le subcommand."""

    def test_le_no_subcommand_shows_help(self, capsys):
        """Test le without subcommand shows help."""
        with patch.object(sys, "argv", ["zxtool", "le"]):
            cli.main()
        captured = capsys.readouterr()
        assert "le" in captured.out.lower() or "encrypt" in captured.out.lower()

    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch(self, mock_batch, capsys):
        """Test le batch command."""
        with patch.object(sys, "argv", ["zxtool", "le", "batch"]):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path=None,
            dry_run=False,
        )

    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch_with_config(self, mock_batch, capsys):
        """Test le batch command with config path."""
        with patch.object(
            sys, "argv", ["zxtool", "le", "batch", "--le-config", "/path/to/zxtool.toml"]
        ):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path="/path/to/zxtool.toml",
            dry_run=False,
        )

    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch_dry_run(self, mock_batch, capsys):
        """Test le batch dry-run command."""
        with patch.object(sys, "argv", ["zxtool", "le", "batch", "--dry-run"]):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path=None,
            dry_run=True,
        )

    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch_with_config_and_dry_run(self, mock_batch, capsys):
        """Test le batch with config and dry-run."""
        with patch.object(
            sys, "argv",
            ["zxtool", "le", "batch", "--le-config", "/custom.toml", "--dry-run"]
        ):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path="/custom.toml",
            dry_run=True,
        )

    @patch("zxtoolbox.letsencrypt.init")
    def test_le_init(self, mock_init, capsys):
        """Test le init command."""
        with patch.object(sys, "argv", ["zxtool", "le", "init"]):
            cli.main()
        mock_init.assert_called_once()

    @patch("zxtoolbox.letsencrypt.show_status")
    def test_le_status(self, mock_status, capsys):
        """Test le status command."""
        with patch.object(sys, "argv", ["zxtool", "le", "status"]):
            cli.main()
        mock_status.assert_called_once()