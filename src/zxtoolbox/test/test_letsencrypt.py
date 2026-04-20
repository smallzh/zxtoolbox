"""Tests for zxtoolbox.letsencrypt module - acme.sh wrapper."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from zxtoolbox.letsencrypt import (
    AcmeShManager,
    CertificateManager,
    CronManager,
    AcmeShError,
    DNS_PROVIDER_MAP,
    HTTP_PROVIDER_MAP,
    init,
    obtain_cert,
    renew_certs,
    show_status,
    revoke_cert,
    batch_obtain_certs,
    batch_renew_certs,
    install_cronjob,
    uninstall_cronjob,
)


class TestAcmeShManager:
    """Test AcmeShManager class."""

    def test_init_default(self):
        """Test default initialization."""
        manager = AcmeShManager()
        assert manager.install_dir == Path.home() / ".acme.sh"
        assert manager.bin_path == Path.home() / ".acme.sh" / "acme.sh"

    def test_init_custom_path(self, tmp_path):
        """Test custom installation path."""
        manager = AcmeShManager(install_dir=str(tmp_path))
        assert manager.install_dir == tmp_path
        assert manager.bin_path == tmp_path / "acme.sh"

    def test_is_installed_true(self, tmp_path):
        """Test is_installed returns True when binary exists."""
        # 创建模拟的 acme.sh 文件
        acme_sh = tmp_path / "acme.sh"
        acme_sh.write_text("#!/bin/bash\necho 'test'")
        acme_sh.chmod(0o755)

        manager = AcmeShManager(install_dir=str(tmp_path))
        assert manager.is_installed() is True

    def test_is_installed_false(self, tmp_path):
        """Test is_installed returns False when binary doesn't exist."""
        manager = AcmeShManager(install_dir=str(tmp_path))
        assert manager.is_installed() is False

    def test_get_version_success(self, tmp_path):
        """Test get_version with successful command."""
        acme_sh = tmp_path / "acme.sh"
        acme_sh.write_text("#!/bin/bash\necho 'v3.0.0'")
        acme_sh.chmod(0o755)

        manager = AcmeShManager(install_dir=str(tmp_path))
        version = manager.get_version()
        assert version == "3.0.0"

    def test_get_version_not_installed(self, tmp_path):
        """Test get_version when not installed."""
        manager = AcmeShManager(install_dir=str(tmp_path))
        assert manager.get_version() is None

    def test_check_and_install_already_installed(self, tmp_path):
        """Test check_and_install when already installed."""
        acme_sh = tmp_path / "acme.sh"
        acme_sh.write_text("#!/bin/bash\necho 'v3.0.0'")
        acme_sh.chmod(0o755)

        manager = AcmeShManager(install_dir=str(tmp_path))
        assert manager.check_and_install() is True

    @patch("zxtoolbox.letsencrypt.subprocess.run")
    def test_run_acme_sh_success(self, mock_run, tmp_path):
        """Test _run_acme_sh with successful command."""
        acme_sh = tmp_path / "acme.sh"
        acme_sh.write_text("#!/bin/bash\necho 'success'")
        acme_sh.chmod(0o755)

        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")

        manager = AcmeShManager(install_dir=str(tmp_path))
        result = manager._run_acme_sh("--version")
        assert result.returncode == 0

    def test_run_acme_sh_not_installed(self, tmp_path):
        """Test _run_acme_sh raises error when not installed."""
        manager = AcmeShManager(install_dir=str(tmp_path))
        with pytest.raises(AcmeShError, match="未安装"):
            manager._run_acme_sh("--version")


class TestCertificateManager:
    """Test CertificateManager class."""

    def test_init_default(self):
        """Test default initialization."""
        acme = AcmeShManager()
        manager = CertificateManager(acme=acme)
        assert manager.acme == acme
        assert manager.staging is True
        assert manager.email == ""

    def test_init_custom(self):
        """Test custom initialization."""
        acme = AcmeShManager()
        manager = CertificateManager(
            acme=acme,
            cert_dir="/test/certs",
            staging=False,
            email="test@example.com",
        )
        assert manager.cert_dir == Path("/test/certs")
        assert manager.staging is False
        assert manager.email == "test@example.com"

    def test_get_dns_env_cloudflare(self):
        """Test _get_dns_env for Cloudflare."""
        acme = AcmeShManager()
        manager = CertificateManager(acme=acme)

        config = {"api_token": "test_token", "zone_id": "test_zone"}
        env = manager._get_dns_env("dns_cf", config)

        assert env == {"CF_Token": "test_token", "CF_Zone_ID": "test_zone"}

    def test_get_dns_env_aliyun(self):
        """Test _get_dns_env for Aliyun."""
        acme = AcmeShManager()
        manager = CertificateManager(acme=acme)

        config = {"access_key_id": "test_id", "access_key_secret": "test_secret"}
        env = manager._get_dns_env("dns_ali", config)

        assert env == {"Ali_Key": "test_id", "Ali_Secret": "test_secret"}

    def test_get_dns_env_no_config(self):
        """Test _get_dns_env with no config."""
        acme = AcmeShManager()
        manager = CertificateManager(acme=acme)

        env = manager._get_dns_env("dns_cf", None)
        assert env is None

    def test_get_cert_expiry(self, tmp_path):
        """Test _get_cert_expiry with mock certificate."""
        acme = AcmeShManager()
        manager = CertificateManager(acme=acme)

        # 创建模拟证书文件（我们需要模拟 openssl 命令）
        cert_file = tmp_path / "test.crt"
        cert_file.write_text("mock certificate")

        with patch("zxtoolbox.letsencrypt.shutil.which") as mock_which:
            mock_which.return_value = "openssl"

            with patch("zxtoolbox.letsencrypt.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="notAfter=Dec  7 10:00:00 2025 GMT",
                )

                expiry = manager._get_cert_expiry(cert_file)
                assert expiry is not None
                assert expiry.year == 2025

    @patch.object(AcmeShManager, "_run_acme_sh")
    @patch.object(CertificateManager, "_get_cert_expiry")
    def test_issue_cert_success(self, mock_expiry, mock_run, tmp_path):
        """Test issue_cert success."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_expiry.return_value = None

        acme = AcmeShManager(install_dir=str(tmp_path))
        # 创建模拟的 acme.sh 二进制文件
        (tmp_path / "acme.sh").write_text("#!/bin/bash")
        (tmp_path / "acme.sh").chmod(0o755)

        manager = CertificateManager(
            acme=acme,
            cert_dir=str(tmp_path / "certs"),
            staging=True,
            email="test@example.com",
        )

        with patch.object(acme, "check_and_install"):
            result = manager.issue_cert(
                domains=["example.com"],
                http_provider="webroot",
                webroot="/var/www/html",
            )
            assert result is not None
            assert result["domain"] == "example.com"

    def test_issue_cert_empty_domains(self, tmp_path):
        """Test issue_cert with empty domains raises ValueError."""
        acme = AcmeShManager(install_dir=str(tmp_path))
        manager = CertificateManager(acme=acme)

        with pytest.raises(ValueError, match="不能为空"):
            manager.issue_cert(domains=[])

    def test_wildcard_requires_dns01(self, tmp_path):
        """Test wildcard domain requires DNS-01 challenge."""
        acme = AcmeShManager(install_dir=str(tmp_path))
        (tmp_path / "acme.sh").write_text("#!/bin/bash")
        (tmp_path / "acme.sh").chmod(0o755)

        manager = CertificateManager(acme=acme)

        with patch.object(acme, "check_and_install"):
            # 泛域名必须使用 DNS-01
            result = manager.issue_cert(
                domains=["*.example.com"],
                dns_provider="manual",
            )
            # 应该成功，因为我们指定了 dns_provider
            assert result is not None

    @patch.object(AcmeShManager, "_run_acme_sh")
    @patch.object(CertificateManager, "_install_cert")
    @patch.object(CertificateManager, "_update_renew_state")
    def test_renew_certs(self, mock_update, mock_install, mock_run, tmp_path):
        """Test renew_certs."""
        mock_run.return_value = MagicMock(returncode=0)

        acme = AcmeShManager(install_dir=str(tmp_path))
        (tmp_path / "acme.sh").write_text("#!/bin/bash")
        (tmp_path / "acme.sh").chmod(0o755)

        # 创建状态文件
        certs_dir = tmp_path / "certs"
        certs_dir.mkdir()
        state = {
            "certificates": {
                "example.com": {
                    "domains": ["example.com"],
                    "provider": "dns_cf",
                    "staging": True,
                    "email": "test@example.com",
                    "issued_at": "2025-01-01T00:00:00+00:00",
                    "expires_at": "2025-12-01T00:00:00+00:00",
                }
            }
        }
        (certs_dir / "renew_state.json").write_text(json.dumps(state))

        manager = CertificateManager(
            acme=acme,
            cert_dir=str(certs_dir),
        )

        with patch.object(acme, "check_and_install"):
            results = manager.renew_certs(force=True)
            assert len(results) > 0

    @patch.object(AcmeShManager, "_run_acme_sh")
    @patch.object(CertificateManager, "_remove_from_state")
    def test_revoke_cert(self, mock_remove, mock_run, tmp_path):
        """Test revoke_cert."""
        mock_run.return_value = MagicMock(returncode=0)

        acme = AcmeShManager(install_dir=str(tmp_path))
        (tmp_path / "acme.sh").write_text("#!/bin/bash")
        (tmp_path / "acme.sh").chmod(0o755)

        manager = CertificateManager(acme=acme)

        with patch.object(acme, "check_and_install"):
            result = manager.revoke_cert("example.com")
            assert result is True

    def test_get_cert_status_empty(self, tmp_path):
        """Test get_cert_status with no certificates."""
        acme = AcmeShManager(install_dir=str(tmp_path))
        manager = CertificateManager(
            acme=acme,
            cert_dir=str(tmp_path),
        )

        status = manager.get_cert_status()
        assert status == []

    def test_get_cert_status_with_certs(self, tmp_path):
        """Test get_cert_status with certificates."""
        acme = AcmeShManager(install_dir=str(tmp_path))

        # 创建状态文件 - 使用足够远的未来日期
        from datetime import datetime, timedelta, timezone
        future_date = datetime.now(timezone.utc) + timedelta(days=365)
        state = {
            "certificates": {
                "example.com": {
                    "domains": ["example.com", "*.example.com"],
                    "provider": "dns_cf",
                    "staging": True,
                    "email": "test@example.com",
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": future_date.isoformat(),
                }
            }
        }
        (tmp_path / "renew_state.json").write_text(json.dumps(state))

        manager = CertificateManager(
            acme=acme,
            cert_dir=str(tmp_path),
        )

        status = manager.get_cert_status()
        assert len(status) == 1
        assert status[0]["domain"] == "example.com"
        assert status[0]["status"] == "valid"


class TestCronManager:
    """Test CronManager class."""

    @patch.object(AcmeShManager, "_run_acme_sh")
    def test_install_cronjob(self, mock_run, tmp_path):
        """Test install_cronjob."""
        mock_run.return_value = MagicMock(returncode=0)

        acme = AcmeShManager(install_dir=str(tmp_path))
        (tmp_path / "acme.sh").write_text("#!/bin/bash")
        (tmp_path / "acme.sh").chmod(0o755)

        cron_manager = CronManager(acme=acme)

        with patch.object(acme, "check_and_install"):
            result = cron_manager.install_cronjob()
            assert result is True

    @patch.object(AcmeShManager, "_run_acme_sh")
    def test_uninstall_cronjob(self, mock_run, tmp_path):
        """Test uninstall_cronjob."""
        mock_run.return_value = MagicMock(returncode=0)

        acme = AcmeShManager(install_dir=str(tmp_path))
        (tmp_path / "acme.sh").write_text("#!/bin/bash")
        (tmp_path / "acme.sh").chmod(0o755)

        cron_manager = CronManager(acme=acme)

        with patch.object(acme, "check_and_install"):
            result = cron_manager.uninstall_cronjob()
            assert result is True


class TestInit:
    """Test init function."""

    def test_init_creates_directory(self, tmp_path):
        """Test init creates directory and state file."""
        cert_dir = tmp_path / "test_certs"
        init(str(cert_dir))

        assert cert_dir.exists()
        state_file = cert_dir / "renew_state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert "certificates" in state

    def test_init_existing_directory(self, tmp_path):
        """Test init with existing directory."""
        cert_dir = tmp_path / "test_certs"
        cert_dir.mkdir()

        init(str(cert_dir))
        assert cert_dir.exists()


class TestObtainCert:
    """Test obtain_cert function."""

    @patch("zxtoolbox.letsencrypt.CertificateManager.issue_cert")
    @patch.object(AcmeShManager, "check_and_install")
    def test_obtain_cert_success(self, mock_check, mock_issue, tmp_path):
        """Test obtain_cert success."""
        mock_issue.return_value = {
            "domain": "example.com",
            "cert_file": "/test/cert.crt",
        }

        result = obtain_cert(
            out_dir=tmp_path,
            domains=["example.com"],
            provider="webroot",
            provider_config={"webroot": "/var/www/html"},
            challenge_type="http-01",
        )

        assert result is not None
        assert result["domain"] == "example.com"

    def test_obtain_cert_wildcard_http01_fails(self, tmp_path, capsys):
        """Test obtain_cert with wildcard and HTTP-01 fails."""
        result = obtain_cert(
            out_dir=tmp_path,
            domains=["*.example.com"],
            provider="webroot",
            challenge_type="http-01",
        )

        assert result is None
        captured = capsys.readouterr()
        assert "泛域名" in captured.out


class TestRenewCerts:
    """Test renew_certs function."""

    @patch("zxtoolbox.letsencrypt.CertificateManager.renew_certs")
    @patch("zxtoolbox.letsencrypt.CertificateManager.get_cert_status")
    @patch.object(AcmeShManager, "check_and_install")
    def test_renew_certs_dry_run(self, mock_check, mock_status, mock_renew, tmp_path):
        """Test renew_certs with dry_run."""
        mock_status.return_value = [
            {
                "domain": "example.com",
                "status": "valid",
                "days_left": 60,
                "expires_at": "2025-12-01T00:00:00+00:00",
            }
        ]

        results = renew_certs(tmp_path, dry_run=True)
        assert results == mock_status.return_value

    @patch("zxtoolbox.letsencrypt.CertificateManager.renew_certs")
    @patch.object(AcmeShManager, "check_and_install")
    def test_renew_certs_actual(self, mock_check, mock_renew, tmp_path):
        """Test renew_certs actual execution."""
        mock_renew.return_value = [
            {"domain": "example.com", "renewed": True}
        ]

        results = renew_certs(tmp_path, dry_run=False)
        assert len(results) == 1


class TestShowStatus:
    """Test show_status function."""

    @patch("zxtoolbox.letsencrypt.renew_certs")
    def test_show_status(self, mock_renew, tmp_path):
        """Test show_status calls renew_certs with dry_run."""
        show_status(tmp_path)
        mock_renew.assert_called_once_with(tmp_path, dry_run=True)


class TestRevokeCert:
    """Test revoke_cert function."""

    @patch("zxtoolbox.letsencrypt.CertificateManager.revoke_cert")
    @patch.object(AcmeShManager, "check_and_install")
    def test_revoke_cert_success(self, mock_check, mock_revoke, tmp_path):
        """Test revoke_cert success."""
        mock_revoke.return_value = True

        result = revoke_cert(tmp_path, "example.com")
        assert result is True


class TestBatchObtainCerts:
    """Test batch_obtain_certs function."""

    @patch("zxtoolbox.config_manager.load_projects_with_domain")
    @patch("zxtoolbox.letsencrypt.obtain_cert")
    def test_batch_obtain_no_projects(self, mock_obtain, mock_load, tmp_path, capsys):
        """Test batch_obtain with no domain projects."""
        mock_load.return_value = []

        results = batch_obtain_certs(str(tmp_path / "config.toml"))
        assert results == {}

    @patch("zxtoolbox.config_manager.load_projects_with_domain")
    @patch("zxtoolbox.letsencrypt.obtain_cert")
    def test_batch_obtain_dry_run(self, mock_obtain, mock_load, tmp_path, capsys):
        """Test batch_obtain with dry_run."""
        mock_load.return_value = [
            {
                "project_dir": "/test",
                "domain": "example.com",
                "_le": {
                    "provider": "manual",
                    "staging": True,
                    "challenge_type": "dns-01",
                }
            }
        ]

        results = batch_obtain_certs(str(tmp_path / "config.toml"), dry_run=True)
        assert "example.com" in results
        assert results["example.com"] is True


class TestBatchRenewCerts:
    """Test batch_renew_certs function."""

    @patch("zxtoolbox.config_manager.load_projects_with_domain")
    @patch("zxtoolbox.letsencrypt.renew_certs")
    def test_batch_renew_no_projects(self, mock_renew, mock_load, tmp_path):
        """Test batch_renew with no domain projects."""
        mock_load.return_value = []
        mock_renew.return_value = []

        results = batch_renew_certs(str(tmp_path / "config.toml"))
        assert results == {}


class TestInstallCronjob:
    """Test install_cronjob function."""

    @patch.object(CronManager, "install_cronjob")
    def test_install_cronjob(self, mock_install):
        """Test install_cronjob."""
        mock_install.return_value = True
        result = install_cronjob()
        assert result is True


class TestUninstallCronjob:
    """Test uninstall_cronjob function."""

    @patch.object(CronManager, "uninstall_cronjob")
    def test_uninstall_cronjob(self, mock_uninstall):
        """Test uninstall_cronjob."""
        mock_uninstall.return_value = True
        result = uninstall_cronjob()
        assert result is True


class TestProviderMaps:
    """Test provider mapping constants."""

    def test_dns_provider_map(self):
        """Test DNS_PROVIDER_MAP contains expected providers."""
        assert "manual" in DNS_PROVIDER_MAP
        assert "cloudflare" in DNS_PROVIDER_MAP
        assert "aliyun" in DNS_PROVIDER_MAP
        assert DNS_PROVIDER_MAP["cloudflare"] == "dns_cf"
        assert DNS_PROVIDER_MAP["aliyun"] == "dns_ali"

    def test_http_provider_map(self):
        """Test HTTP_PROVIDER_MAP contains expected providers."""
        assert "webroot" in HTTP_PROVIDER_MAP
        assert "standalone" in HTTP_PROVIDER_MAP


class TestAcmeShError:
    """Test AcmeShError exception."""

    def test_error_creation(self):
        """Test creating AcmeShError."""
        error = AcmeShError("Test error message")
        assert str(error) == "Test error message"
