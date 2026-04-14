"""Tests for zxtoolbox.nginx_manager module."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from zxtoolbox.nginx_manager import (
    check_nginx,
    generate_site_config,
    generate_from_config,
    write_site_config,
    _domain_to_filename,
    _find_config_dir,
    _find_sites_dir,
    enable_site,
    disable_site,
    reload_nginx,
    NGINX_SITE_TEMPLATE,
    NGINX_HTTP_ONLY_TEMPLATE,
)


class TestDomainToFilename:
    """Test domain to filename conversion."""

    def test_simple_domain(self):
        """Test simple domain conversion."""
        assert _domain_to_filename("example.com") == "example.com"

    def test_wildcard_domain(self):
        """Test wildcard domain conversion."""
        assert _domain_to_filename("*.example.com") == "wildcard.example.com"

    def test_subdomain(self):
        """Test subdomain conversion."""
        assert _domain_to_filename("www.example.com") == "www.example.com"


class TestGenerateSiteConfig:
    """Test Nginx site config generation."""

    def test_generate_https_config(self):
        """Test generating HTTPS config with SSL certificates."""
        config = generate_site_config(
            domain="example.com",
            root="/var/www/example",
            ssl_certificate="/etc/letsencrypt/live/example.com/fullchain.pem",
            ssl_certificate_key="/etc/letsencrypt/live/example.com/privkey.pem",
        )

        assert "server_name example.com" in config
        assert "listen 443 ssl http2" in config
        assert "listen 80" in config
        assert "ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem" in config
        assert "ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem" in config
        assert "root /var/www/example" in config
        assert "return 301 https://$host$request_uri" in config
        assert "Strict-Transport-Security" in config

    def test_generate_http_only_config(self):
        """Test generating HTTP-only config without SSL."""
        config = generate_site_config(
            domain="example.com",
            root="/var/www/example",
        )

        assert "server_name example.com" in config
        assert "listen 80" in config
        assert "listen 443" not in config
        assert "root /var/www/example" in config
        assert "ssl_certificate" not in config

    def test_generate_with_custom_server_name(self):
        """Test generating config with custom server_name."""
        config = generate_site_config(
            domain="example.com",
            root="/var/www/example",
            server_name="example.com www.example.com",
        )

        assert "server_name example.com www.example.com" in config

    def test_generate_with_custom_webroot(self):
        """Test generating config with custom webroot for ACME."""
        config = generate_site_config(
            domain="example.com",
            root="/var/www/example",
            webroot="/var/www/html",
        )

        assert "root /var/www/html" in config or "/var/www/html" in config

    def test_generate_wildcard_domain_https(self):
        """Test generating config for wildcard domain."""
        config = generate_site_config(
            domain="*.example.com",
            root="/var/www/example",
            ssl_certificate="/path/to/cert",
            ssl_certificate_key="/path/to/key",
        )

        assert "server_name *.example.com" in config
        assert "listen 443 ssl http2" in config


class TestWriteSiteConfig:
    """Test writing Nginx config files."""

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_write_to_explicit_output_dir(self, mock_sites_dir, tmp_path):
        """Test writing config to explicit output directory."""
        mock_sites_dir.return_value = (None, None)

        config_content = "server { listen 80; }"
        output_dir = tmp_path / "nginx_configs"

        result = write_site_config(
            domain="example.com",
            config_content=config_content,
            output_dir=str(output_dir),
        )

        assert result.exists()
        assert result.name == "example.com.conf"
        assert result.read_text() == config_content

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_write_wildcard_domain_filename(self, mock_sites_dir, tmp_path):
        """Test that wildcard domain gets correct filename."""
        mock_sites_dir.return_value = (None, None)

        config_content = "server { listen 80; }"
        output_dir = tmp_path / "nginx_configs"

        result = write_site_config(
            domain="*.example.com",
            config_content=config_content,
            output_dir=str(output_dir),
        )

        assert result.name == "wildcard.example.com.conf"


class TestCheckNginx:
    """Test Nginx availability check."""

    @patch("zxtoolbox.nginx_manager.shutil.which")
    def test_nginx_not_installed(self, mock_which):
        """Test check when nginx is not installed."""
        mock_which.return_value = None

        result = check_nginx()

        assert result["available"] is False
        assert result["version"] is None
        assert result["nginx_path"] is None

    @patch("zxtoolbox.nginx_manager.shutil.which")
    @patch("zxtoolbox.nginx_manager.subprocess.run")
    def test_nginx_installed(self, mock_run, mock_which):
        """Test check when nginx is installed."""
        mock_which.return_value = "/usr/sbin/nginx"
        # Mock version output
        version_result = MagicMock(stderr="nginx version: nginx/1.24.0\n")
        # Mock config output
        config_result = MagicMock(
            stdout="",
            stderr="--conf-path=/etc/nginx/nginx.conf\n"
        )
        mock_run.side_effect = [version_result, config_result]

        with patch.object(Path, "exists", return_value=True):
            result = check_nginx()

        assert result["available"] is True
        assert result["nginx_path"] == "/usr/sbin/nginx"

    @patch("zxtoolbox.nginx_manager.shutil.which")
    @patch("zxtoolbox.nginx_manager.subprocess.run")
    def test_nginx_version_parsed(self, mock_run, mock_which):
        """Test that nginx version is correctly parsed."""
        mock_which.return_value = "/usr/sbin/nginx"
        version_result = MagicMock(stderr="nginx version: nginx/1.24.0\n")
        config_result = MagicMock(stdout="", stderr="")
        mock_run.side_effect = [version_result, config_result]

        result = check_nginx()

        assert result["version"] is not None
        assert "1.24.0" in result["version"]


class TestEnableDisableSite:
    """Test site enable/disable operations."""

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_enable_site_success(self, mock_sites_dir, tmp_path):
        """Test enabling a site successfully."""
        sites_available = tmp_path / "sites-available"
        sites_enabled = tmp_path / "sites-enabled"
        sites_available.mkdir()
        sites_enabled.mkdir()

        config_file = sites_available / "example.com.conf"
        config_file.write_text("server { listen 80; }")

        mock_sites_dir.return_value = (sites_available, sites_enabled)

        result = enable_site("example.com")

        assert result is True
        assert (sites_enabled / "example.com.conf").exists()

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_enable_site_already_enabled(self, mock_sites_dir, tmp_path, capsys):
        """Test enabling a site that is already enabled."""
        sites_available = tmp_path / "sites-available"
        sites_enabled = tmp_path / "sites-enabled"
        sites_available.mkdir()
        sites_enabled.mkdir()

        config_file = sites_available / "example.com.conf"
        config_file.write_text("server { listen 80; }")
        # Pre-create the symlink
        (sites_enabled / "example.com.conf").symlink_to(config_file)

        mock_sites_dir.return_value = (sites_available, sites_enabled)

        result = enable_site("example.com")

        assert result is True

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_enable_site_config_not_found(self, mock_sites_dir, tmp_path, capsys):
        """Test enabling a site when config doesn't exist."""
        sites_available = tmp_path / "sites-available"
        sites_enabled = tmp_path / "sites-enabled"
        sites_available.mkdir()
        sites_enabled.mkdir()

        mock_sites_dir.return_value = (sites_available, sites_enabled)

        result = enable_site("nonexistent.com")

        assert result is False
        captured = capsys.readouterr()
        assert "不存在" in captured.out

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_enable_site_no_sites_dir(self, mock_sites_dir, capsys):
        """Test enabling when sites directory doesn't exist."""
        mock_sites_dir.return_value = (None, None)

        result = enable_site("example.com")

        assert result is False
        captured = capsys.readouterr()
        assert "未找到" in captured.out

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_disable_site_success(self, mock_sites_dir, tmp_path):
        """Test disabling a site successfully."""
        sites_available = tmp_path / "sites-available"
        sites_enabled = tmp_path / "sites-enabled"
        sites_available.mkdir()
        sites_enabled.mkdir()

        config_file = sites_available / "example.com.conf"
        config_file.write_text("server { listen 80; }")
        symlink = sites_enabled / "example.com.conf"
        symlink.symlink_to(config_file)

        mock_sites_dir.return_value = (sites_available, sites_enabled)

        result = disable_site("example.com")

        assert result is True
        assert not symlink.exists()

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_disable_site_not_enabled(self, mock_sites_dir, tmp_path, capsys):
        """Test disabling a site that is not enabled."""
        sites_available = tmp_path / "sites-available"
        sites_enabled = tmp_path / "sites-enabled"
        sites_available.mkdir()
        sites_enabled.mkdir()

        mock_sites_dir.return_value = (sites_available, sites_enabled)

        result = disable_site("example.com")

        assert result is True

    @patch("zxtoolbox.nginx_manager._find_sites_dir")
    def test_disable_site_no_sites_dir(self, mock_sites_dir, capsys):
        """Test disabling when sites directory doesn't exist."""
        mock_sites_dir.return_value = (None, None)

        result = disable_site("example.com")

        assert result is False


class TestReloadNginx:
    """Test Nginx reload."""

    @patch("zxtoolbox.nginx_manager.shutil.which")
    def test_reload_nginx_not_installed(self, mock_which, capsys):
        """Test reload when nginx is not installed."""
        mock_which.return_value = None

        result = reload_nginx()

        assert result is False
        captured = capsys.readouterr()
        assert "未安装" in captured.out

    @patch("zxtoolbox.nginx_manager.shutil.which")
    @patch("zxtoolbox.nginx_manager.subprocess.run")
    def test_reload_nginx_success(self, mock_run, mock_which, capsys):
        """Test successful nginx reload."""
        mock_which.return_value = "/usr/sbin/nginx"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = reload_nginx()

        assert result is True
        captured = capsys.readouterr()
        assert "已重载" in captured.out

    @patch("zxtoolbox.nginx_manager.shutil.which")
    @patch("zxtoolbox.nginx_manager.subprocess.run")
    def test_reload_nginx_failure(self, mock_run, mock_which, capsys):
        """Test nginx reload failure."""
        mock_which.return_value = "/usr/sbin/nginx"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="nginx: [emerg] invalid parameter"
        )

        result = reload_nginx()

        assert result is False


class TestGenerateFromConfig:
    """Test generating Nginx configs from zxtool.toml."""

    @patch("zxtoolbox.nginx_manager.write_site_config")
    @patch("zxtoolbox.nginx_manager.load_config")
    def test_generate_with_domains(self, mock_load, mock_write, tmp_path):
        """Test generating configs for projects with domains."""
        mock_load.return_value = {
            "letsencrypt": {
                "provider": "manual",
                "output_dir": "out_le",
            },
            "projects": [
                {
                    "project_dir": "/path/to/project1",
                    "domain": "example.com",
                    "output_dir": "/var/www/example",
                },
                {
                    "project_dir": "/path/to/project2",
                    "domain": "*.example.org",
                },
            ],
        }
        mock_write.return_value = Path("/etc/nginx/sites-available/example.com.conf")

        config_file = tmp_path / "zxtool.toml"
        config_file.write_text("[letsencrypt]\nprovider = 'manual'\n")

        result = generate_from_config(
            config_path=str(config_file),
            output_dir=str(tmp_path / "nginx"),
        )

        assert "example.com" in result
        assert "*.example.org" in result
        assert mock_write.call_count == 2

    @patch("zxtoolbox.nginx_manager.load_config")
    def test_generate_no_domains(self, mock_load, tmp_path, capsys):
        """Test generating configs when no projects have domains."""
        mock_load.return_value = {
            "projects": [
                {"project_dir": "/path/to/project1"},
            ],
        }

        config_file = tmp_path / "zxtool.toml"
        config_file.write_text("[[projects]]\nproject_dir = '/path'\n")

        result = generate_from_config(config_path=str(config_file))

        assert result == {}
        captured = capsys.readouterr()
        assert "没有配置 domain" in captured.out

    @patch("zxtoolbox.nginx_manager.load_config")
    def test_generate_config_not_found(self, mock_load, capsys):
        """Test generating configs when config file doesn't exist."""
        mock_load.side_effect = FileNotFoundError("Config not found")

        result = generate_from_config(config_path="/nonexistent/path.toml")

        assert result == {}

    @patch("zxtoolbox.nginx_manager.write_site_config")
    @patch("zxtoolbox.nginx_manager.load_config")
    def test_generate_dry_run(self, mock_load, mock_write, tmp_path, capsys):
        """Test dry-run mode."""
        mock_load.return_value = {
            "letsencrypt": {
                "provider": "manual",
                "output_dir": "out_le",
            },
            "projects": [
                {
                    "project_dir": "/path/to/project",
                    "domain": "example.com",
                },
            ],
        }

        config_file = tmp_path / "zxtool.toml"
        config_file.write_text("[letsencrypt]\nprovider = 'manual'\n")

        result = generate_from_config(
            config_path=str(config_file),
            dry_run=True,
        )

        mock_write.assert_not_called()