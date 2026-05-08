"""Tests for zxtoolbox.cli module."""

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from zxtoolbox import cli


@pytest.fixture(autouse=True)
def _reset_logging_state():
    """Reset logging state between tests."""
    from zxtoolbox.logging_manager import reset_logging

    reset_logging()
    yield
    reset_logging()

    pkg_logger = logging.getLogger("zxtoolbox")
    for handler in pkg_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
        pkg_logger.removeHandler(handler)


class TestCliMain:
    """Test top-level CLI behavior."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_main_no_args_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool"]):
            cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "zxtool" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_main_help_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "--help"]):
            with pytest.raises(SystemExit):
                cli.main()
        captured = capsys.readouterr()
        assert "zxtool" in captured.out.lower() or "usage" in captured.out.lower()


class TestCliComputer:
    """Test CLI ci subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.computer_info.summary_info")
    def test_ci_default_shows_summary(self, mock_summary, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "ci"]):
            cli.main()
        mock_summary.assert_called_once()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.computer_info.detailed_info")
    def test_ci_all_shows_detailed(self, mock_detailed, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "ci", "--all"]):
            cli.main()
        mock_detailed.assert_called_once()


class TestCliTotp:
    """Test CLI totp subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.pyopt_2fa.parseTotpCdoe")
    def test_totp_with_key(self, mock_parse, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "totp", "-k", "TESTKEY"]):
            cli.main()
        mock_parse.assert_called_once_with("TESTKEY")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_totp_without_key_shows_error(self, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "totp"]):
            with pytest.raises(SystemExit):
                cli.main()


class TestCliVideo:
    """Test CLI video subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.video_download.download_with_progress")
    def test_video_with_url(self, mock_download, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "video", "-u", "https://example.com"]):
            cli.main()
        mock_download.assert_called_once_with("https://example.com", None)

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.video_download.download_with_progress")
    def test_video_with_url_and_output(self, mock_download, _mock_setup_log):
        with patch.object(
            sys,
            "argv",
            ["zxtool", "video", "-u", "https://example.com", "-o", "/tmp/vid.mp4"],
        ):
            cli.main()
        mock_download.assert_called_once_with("https://example.com", "/tmp/vid.mp4")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_video_without_url_shows_error(self, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "video"]):
            with pytest.raises(SystemExit):
                cli.main()


class TestCliHttp:
    """Test CLI http subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_http_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "http"]):
            cli.main()
        captured = capsys.readouterr()
        assert "http" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.http_server.serve_directory")
    def test_http_serve_default(self, mock_serve, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "http", "serve"]):
            cli.main()
        mock_serve.assert_called_once_with(
            directory=".",
            host="127.0.0.1",
            port=8000,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.http_server.serve_directory")
    def test_http_serve_with_custom_options(self, mock_serve, _mock_setup_log):
        with patch.object(
            sys,
            "argv",
            ["zxtool", "http", "serve", "./site", "--host", "0.0.0.0", "--port", "9000"],
        ):
            cli.main()
        mock_serve.assert_called_once_with(
            directory="./site",
            host="0.0.0.0",
            port=9000,
        )


class TestCliSsl:
    """Test CLI ssl subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_ssl_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "ssl"]):
            cli.main()
        captured = capsys.readouterr()
        assert "ssl" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.ssl_cert.init")
    def test_ssl_init(self, mock_init, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "ssl", "init"]):
            cli.main()
        mock_init.assert_called_once()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.ssl_cert.generate_root")
    def test_ssl_root(self, mock_root, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "ssl", "root"]):
            cli.main()
        mock_root.assert_called_once()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.ssl_cert.generate_cert")
    def test_ssl_cert(self, mock_cert, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "ssl", "cert", "-d", "example.dev"]):
            cli.main()
        mock_cert.assert_called_once()


class TestCliEpub:
    """Test CLI epub subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_epub_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "epub"]):
            cli.main()
        captured = capsys.readouterr()
        assert "epub" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.epub_manager.convert_epub_to_markdown")
    def test_epub_convert(self, mock_convert, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "epub", "convert", "book.epub", "-o", "out_dir"]):
            cli.main()
        mock_convert.assert_called_once_with(epub_file="book.epub", output_dir="out_dir")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.epub_manager.convert_epub_to_markdown", side_effect=ValueError("Invalid EPUB file: bad data"))
    def test_epub_convert_prints_user_friendly_error(self, _mock_convert, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "epub", "convert", "broken.epub"]):
            cli.main()
        captured = capsys.readouterr()
        assert "[ERROR] Invalid EPUB file: bad data" in captured.out


class TestCliBackup:
    """Test CLI backup subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_backup_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "backup"]):
            cli.main()
        captured = capsys.readouterr()
        assert "backup" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.backup_manager.copy_directory_with_backup")
    def test_backup_copy(self, mock_copy, _mock_setup_log):
        with patch.object(
            sys,
            "argv",
            [
                "zxtool",
                "backup",
                "copy",
                "src_dir",
                "dst_dir",
                "--backup-dir-name",
                ".bak",
                "--backup-log-name",
                "records.md",
                "--commit-message",
                "sync files",
            ],
        ):
            cli.main()
        mock_copy.assert_called_once_with(
            source_dir="src_dir",
            target_dir="dst_dir",
            backup_dir_name=".bak",
            backup_log_name="records.md",
            commit_message="sync files",
        )


class TestCliMkpdf:
    """Test CLI mkpdf command."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkpdf_manager.convert_markdown_to_pdf")
    def test_mkpdf_basic(self, mock_convert, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "mkpdf", "docs/index.md"]):
            cli.main()
        mock_convert.assert_called_once_with(
            input_path="docs/index.md",
            output_path=None,
            title=None,
            directory_file="README.md",
            browser_path=None,
            mermaid_js=None,
            enable_mermaid=True,
            render_wait_ms=5000,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkpdf_manager.convert_markdown_to_pdf")
    def test_mkpdf_with_options(self, mock_convert, _mock_setup_log):
        with patch.object(
            sys,
            "argv",
            [
                "zxtool",
                "mkpdf",
                "docs",
                "--file",
                "guide/index.md",
                "-o",
                "out.pdf",
                "--title",
                "My PDF",
                "--browser",
                "msedge",
                "--mermaid-js",
                "vendor/mermaid.min.js",
                "--no-mermaid",
                "--render-wait-ms",
                "8000",
            ],
        ):
            cli.main()
        mock_convert.assert_called_once_with(
            input_path="docs",
            output_path="out.pdf",
            title="My PDF",
            directory_file="guide/index.md",
            browser_path="msedge",
            mermaid_js="vendor/mermaid.min.js",
            enable_mermaid=False,
            render_wait_ms=8000,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkpdf_manager.convert_markdown_to_pdf", side_effect=FileNotFoundError("missing"))
    def test_mkpdf_prints_user_friendly_error(self, _mock_convert, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "mkpdf", "missing.md"]):
            cli.main()
        captured = capsys.readouterr()
        assert "[ERROR] missing" in captured.out


class TestCliGit:
    """Test CLI git subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_git_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "git"]):
            cli.main()
        captured = capsys.readouterr()
        assert "git" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_git_config_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "git", "config"]):
            cli.main()
        captured = capsys.readouterr()
        assert "config" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.check_git_config")
    def test_git_config_check(self, mock_check, _mock_setup_log, capsys):
        mock_check.return_value = {"name": "Test", "email": "test@test.com"}
        with patch.object(sys, "argv", ["zxtool", "git", "config", "check"]):
            cli.main()
        mock_check.assert_called_once_with(None)
        captured = capsys.readouterr()
        assert "Test" in captured.out

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.fill_git_config")
    def test_git_config_fill(self, mock_fill, _mock_setup_log):
        with patch.object(
            sys,
            "argv",
            ["zxtool", "git", "config", "fill", "--name", "Test", "--email", "test@test.com"],
        ):
            cli.main()
        mock_fill.assert_called_once_with(
            project_dir=None,
            config_file=None,
            name="Test",
            email="test@test.com",
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.check_git_config")
    def test_git_config_check_with_project(self, mock_check, _mock_setup_log):
        mock_check.return_value = None
        with patch.object(sys, "argv", ["zxtool", "git", "config", "check", "/path/to/project"]):
            cli.main()
        mock_check.assert_called_once_with("/path/to/project")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_project_dir(self, mock_pull, _mock_setup_log):
        mock_pull.return_value = True
        with patch.object(sys, "argv", ["zxtool", "git", "pull", "/path/to/project"]):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir="/path/to/project",
            remote=None,
            branch=None,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_remote(self, mock_pull, _mock_setup_log):
        mock_pull.return_value = True
        with patch.object(sys, "argv", ["zxtool", "git", "pull", "--remote", "origin"]):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir=None,
            remote="origin",
            branch=None,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_remote_and_branch(self, mock_pull, _mock_setup_log):
        mock_pull.return_value = True
        with patch.object(sys, "argv", ["zxtool", "git", "pull", "--remote", "upstream", "--branch", "main"]):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir=None,
            remote="upstream",
            branch="main",
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_project_dir_and_remote(self, mock_pull, _mock_setup_log):
        mock_pull.return_value = True
        with patch.object(
            sys,
            "argv",
            ["zxtool", "git", "pull", "/my/project", "--remote", "origin", "--branch", "dev"],
        ):
            cli.main()
        mock_pull.assert_called_once_with(
            project_dir="/my/project",
            remote="origin",
            branch="dev",
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull")
    def test_git_pull_with_git_in_cwd(self, mock_pull, _mock_setup_log):
        mock_pull.return_value = True
        with patch.object(sys, "argv", ["zxtool", "git", "pull"]):
            with patch("zxtoolbox.git_config.find_git_dir", return_value=Path("/cwd/.git")):
                cli.main()
        mock_pull.assert_called_once_with(
            project_dir=None,
            remote=None,
            branch=None,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull_all_projects")
    def test_git_pull_batch_mode(self, mock_batch, _mock_setup_log):
        mock_batch.return_value = []
        with patch.object(sys, "argv", ["zxtool", "git", "pull"]):
            with patch("zxtoolbox.git_config.find_git_dir", return_value=None):
                cli.main()
        mock_batch.assert_called_once_with(
            config_path=None,
            remote=None,
            branch=None,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.git_config.git_pull_all_projects")
    def test_git_pull_batch_with_config(self, mock_batch, _mock_setup_log):
        mock_batch.return_value = []
        with patch.object(sys, "argv", ["zxtool", "git", "pull", "--config", "/custom.toml"]):
            with patch("zxtoolbox.git_config.find_git_dir", return_value=None):
                cli.main()
        mock_batch.assert_called_once_with(
            config_path="/custom.toml",
            remote=None,
            branch=None,
        )


class TestCliConfig:
    """Test CLI config subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_config_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "config"]):
            cli.main()
        captured = capsys.readouterr()
        assert "config" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.config_manager.interactive_init")
    def test_config_init(self, mock_init, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "config", "init"]):
            cli.main()
        mock_init.assert_called_once_with(config_path=None, force=False)

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.config_manager.interactive_init")
    def test_config_init_with_options(self, mock_init, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "config", "init", "--path", "/custom/path", "--force"]):
            cli.main()
        mock_init.assert_called_once_with(config_path="/custom/path", force=True)

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.config_manager.show_config")
    def test_config_show(self, mock_show, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "config", "show"]):
            cli.main()
        mock_show.assert_called_once_with(config_path=None)

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.config_manager.show_config")
    def test_config_show_with_path(self, mock_show, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "config", "show", "--path", "/custom/config.toml"]):
            cli.main()
        mock_show.assert_called_once_with(config_path="/custom/config.toml")


class TestCliMkdocs:
    """Test CLI mkdocs subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_mkdocs_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "mkdocs"]):
            cli.main()
        captured = capsys.readouterr()
        assert "mkdocs" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkdocs_manager.create_project")
    def test_mkdocs_create(self, mock_create, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "mkdocs", "create", "/path/to/project", "--name", "My Site"]):
            cli.main()
        mock_create.assert_called_once_with("/path/to/project", site_name="My Site")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkdocs_manager.build_project")
    def test_mkdocs_build(self, mock_build, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "mkdocs", "build", "/path/to/project", "-o", "/output", "--strict"]):
            cli.main()
        mock_build.assert_called_once_with(
            project_dir="/path/to/project",
            output_dir="/output",
            config_file=None,
            strict=True,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkdocs_manager.batch_build")
    def test_mkdocs_batch(self, mock_batch, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "mkdocs", "batch", "/config.toml", "--dry-run"]):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path="/config.toml",
            dry_run=True,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkdocs_manager.serve_project")
    def test_mkdocs_serve(self, mock_serve, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "mkdocs", "serve", "/path/to/project"]):
            cli.main()
        mock_serve.assert_called_once_with(
            project_dir="/path/to/project",
            dev_addr=None,
            config_file=None,
            no_livereload=False,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.mkdocs_manager.serve_project")
    def test_mkdocs_serve_with_options(self, mock_serve, _mock_setup_log):
        with patch.object(
            sys,
            "argv",
            ["zxtool", "mkdocs", "serve", "/path/to/project", "-a", "0.0.0.0:8080", "--no-livereload"],
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

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_nginx_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "nginx"]):
            cli.main()
        captured = capsys.readouterr()
        assert "nginx" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.nginx_manager.check_nginx")
    def test_nginx_check(self, mock_check, _mock_setup_log, capsys):
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

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.nginx_manager.generate_from_config")
    def test_nginx_generate(self, mock_generate, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "nginx", "generate", "--config", "/path/to/zxtool.toml"]):
            cli.main()
        mock_generate.assert_called_once_with(
            config_path="/path/to/zxtool.toml",
            output_dir=None,
            dry_run=False,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.nginx_manager.generate_from_config")
    def test_nginx_generate_dry_run(self, mock_generate, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "nginx", "generate", "--dry-run"]):
            cli.main()
        mock_generate.assert_called_once_with(
            config_path=None,
            output_dir=None,
            dry_run=True,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.nginx_manager.enable_site")
    def test_nginx_enable(self, mock_enable, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "nginx", "enable", "example.com"]):
            cli.main()
        mock_enable.assert_called_once_with("example.com")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.nginx_manager.disable_site")
    def test_nginx_disable(self, mock_disable, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "nginx", "disable", "example.com"]):
            cli.main()
        mock_disable.assert_called_once_with("example.com")

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.nginx_manager.reload_nginx")
    def test_nginx_reload(self, mock_reload, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "nginx", "reload"]):
            cli.main()
        mock_reload.assert_called_once()


class TestCliLetsEncrypt:
    """Test CLI le subcommand."""

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    def test_le_no_subcommand_shows_help(self, _mock_setup_log, capsys):
        with patch.object(sys, "argv", ["zxtool", "le"]):
            cli.main()
        captured = capsys.readouterr()
        assert "le" in captured.out.lower() or "encrypt" in captured.out.lower()

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch(self, mock_batch, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "le", "batch"]):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path=None,
            dry_run=False,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch_with_config(self, mock_batch, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "le", "batch", "--le-config", "/path/to/zxtool.toml"]):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path="/path/to/zxtool.toml",
            dry_run=False,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.batch_obtain_certs")
    def test_le_batch_dry_run(self, mock_batch, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "le", "batch", "--dry-run"]):
            cli.main()
        mock_batch.assert_called_once_with(
            config_path=None,
            dry_run=True,
        )

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.init")
    def test_le_init(self, mock_init, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "le", "init"]), patch(
            "zxtoolbox.config_manager.load_le_config",
            side_effect=FileNotFoundError,
        ):
            cli.main()
        mock_init.assert_called_once()
        called_path = mock_init.call_args[0][0]
        assert called_path.name == "out_le"

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.init")
    def test_le_init_with_config_output_dir(self, mock_init, _mock_setup_log):
        config_output_dir = "custom_certs"
        with patch.object(sys, "argv", ["zxtool", "le", "init"]), patch(
            "zxtoolbox.config_manager.load_le_config",
            return_value={
                "provider": "manual",
                "output_dir": config_output_dir,
                "staging": True,
                "email": "",
                "provider_config": {},
            },
        ):
            cli.main()
        mock_init.assert_called_once()
        called_path = mock_init.call_args[0][0]
        assert called_path.name == config_output_dir or config_output_dir in str(called_path)

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.init")
    def test_le_init_with_explicit_output(self, mock_init, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "le", "init", "--output", "explicit_path"]):
            cli.main()
        mock_init.assert_called_once()
        called_path = mock_init.call_args[0][0]
        assert called_path.name == "explicit_path"

    @patch("zxtoolbox.logging_manager.setup_logging", return_value=None)
    @patch("zxtoolbox.letsencrypt.show_status")
    def test_le_status(self, mock_status, _mock_setup_log):
        with patch.object(sys, "argv", ["zxtool", "le", "status"]):
            cli.main()
        mock_status.assert_called_once()
