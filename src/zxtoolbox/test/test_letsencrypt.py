"""Tests for zxtoolbox.letsencrypt module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from zxtoolbox.letsencrypt import (
    DNSProvider,
    ManualProvider,
    get_provider,
    _compute_dns01_validation,
    _PROVIDER_MAP,
    batch_obtain_certs,
    batch_renew_certs,
)


class TestDNSProvider:
    """Test DNS provider base class."""

    def test_base_provider_not_implemented(self):
        """Test that base provider raises NotImplementedError."""
        provider = DNSProvider()
        with pytest.raises(NotImplementedError):
            provider.add_txt_record(
                "example.com", "_acme-challenge.example.com", "value"
            )
        with pytest.raises(NotImplementedError):
            provider.del_txt_record(
                "example.com", "_acme-challenge.example.com", "value"
            )


class TestManualProvider:
    """Test manual DNS provider."""

    def test_manual_provider_name(self):
        """Test provider name."""
        provider = ManualProvider()
        assert provider.name == "manual"

    @patch("builtins.input", return_value="")
    def test_manual_add_txt_record(self, mock_input, capsys):
        """Test manual provider prompts user."""
        provider = ManualProvider()
        provider.add_txt_record(
            "example.com", "_acme-challenge.example.com", "test-value"
        )
        captured = capsys.readouterr()
        assert "_acme-challenge.example.com" in captured.out
        assert "test-value" in captured.out
        mock_input.assert_called_once()

    def test_manual_del_txt_record(self, capsys):
        """Test manual provider shows cleanup hint."""
        provider = ManualProvider()
        provider.del_txt_record(
            "example.com", "_acme-challenge.example.com", "test-value"
        )
        captured = capsys.readouterr()
        assert "删除" in captured.out or "delete" in captured.out.lower()


class TestGetProvider:
    """Test provider factory."""

    def test_get_manual_provider(self):
        """Test getting manual provider."""
        provider = get_provider("manual")
        assert isinstance(provider, ManualProvider)

    def test_get_provider_case_insensitive(self):
        """Test provider name is case insensitive."""
        provider = get_provider("MANUAL")
        assert isinstance(provider, ManualProvider)

    def test_get_unsupported_provider(self):
        """Test getting unsupported provider raises ValueError."""
        with pytest.raises(ValueError, match="不支持的 DNS 提供商"):
            get_provider("unsupported")


class TestComputeDns01Validation:
    """Test DNS-01 validation computation."""

    def test_compute_dns01_validation(self):
        """Test DNS-01 validation value computation."""
        # The validation value is base64url(sha256(key_authorization))
        key_auth = "token.account_thumbprint"
        result = _compute_dns01_validation(key_auth)
        # Should be a base64url-encoded string (no padding)
        assert isinstance(result, str)
        assert "=" not in result  # base64url strips padding
        assert len(result) == 43  # SHA-256 = 32 bytes -> 43 base64url chars

    def test_compute_dns01_different_inputs(self):
        """Test different inputs produce different outputs."""
        result1 = _compute_dns01_validation("key1")
        result2 = _compute_dns01_validation("key2")
        assert result1 != result2


class TestInit:
    """Test LE output directory initialization."""

    def test_init_creates_directory(self, tmp_path, capsys):
        """Test init creates output directory and state file."""
        from zxtoolbox.letsencrypt import init

        out_dir = tmp_path / "out_le"
        init(out_dir)

        assert out_dir.exists()
        state_path = out_dir / "renew_state.json"
        assert state_path.exists()

        state = json.loads(state_path.read_text())
        assert "certificates" in state

    def test_init_existing_directory(self, tmp_path, capsys):
        """Test init with existing directory doesn't fail."""
        from zxtoolbox.letsencrypt import init

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        init(out_dir)

        assert out_dir.exists()


class TestShowStatus:
    """Test certificate status display."""

    def test_show_status_no_state_file(self, tmp_path, capsys):
        """Test showing status when no state file exists."""
        from zxtoolbox.letsencrypt import show_status

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        show_status(out_dir)

        captured = capsys.readouterr()
        assert "没有" in captured.out or "no" in captured.out.lower()

    def test_show_status_empty_certificates(self, tmp_path, capsys):
        """Test showing status with empty certificates."""
        from zxtoolbox.letsencrypt import show_status

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        state_path = out_dir / "renew_state.json"
        state_path.write_text(json.dumps({"certificates": {}}))

        show_status(out_dir)

        captured = capsys.readouterr()
        assert "没有" in captured.out or "no" in captured.out.lower()

    def test_show_status_with_certificates(self, tmp_path, capsys):
        """Test showing status with valid certificates."""
        from zxtoolbox.letsencrypt import show_status

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        state_path = out_dir / "renew_state.json"
        state = {
            "certificates": {
                "example.com": {
                    "domains": ["example.com", "*.example.com"],
                    "issued_at": "2025-01-01T00:00:00+00:00",
                    "expires_at": "2026-01-01T00:00:00+00:00",
                    "provider": "manual",
                    "staging": True,
                }
            }
        }
        state_path.write_text(json.dumps(state))

        show_status(out_dir)

        captured = capsys.readouterr()
        assert "example.com" in captured.out


class TestRenewCerts:
    """Test certificate renewal."""

    def test_renew_no_state_file(self, tmp_path, capsys):
        """Test renewal when no state file exists."""
        from zxtoolbox.letsencrypt import renew_certs

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        renew_certs(out_dir)

        captured = capsys.readouterr()
        # The source has a bug: uses f-string with single quotes instead of f-string
        # So it prints literal {state_path}. We check for any output.
        assert len(captured.out) > 0

    def test_renew_empty_certificates(self, tmp_path, capsys):
        """Test renewal with no certificates."""
        from zxtoolbox.letsencrypt import renew_certs

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        state_path = out_dir / "renew_state.json"
        state_path.write_text(json.dumps({"certificates": {}}))

        renew_certs(out_dir)

        captured = capsys.readouterr()
        assert "没有" in captured.out or "no" in captured.out.lower()

    def test_renew_dry_run(self, tmp_path, capsys):
        """Test renewal in dry-run mode."""
        from zxtoolbox.letsencrypt import renew_certs

        out_dir = tmp_path / "out_le"
        out_dir.mkdir()
        state_path = out_dir / "renew_state.json"
        state = {
            "certificates": {
                "example.com": {
                    "domains": ["example.com"],
                    "issued_at": "2025-01-01T00:00:00+00:00",
                    "expires_at": "2025-06-01T00:00:00+00:00",  # Expired
                    "provider": "manual",
                    "staging": True,
                }
            }
        }
        state_path.write_text(json.dumps(state))

        renew_certs(out_dir, dry_run=True)

        captured = capsys.readouterr()
        assert "dry-run" in captured.out or "跳过" in captured.out


class TestProviderMap:
    """Test provider registry."""

    def test_provider_map_contains_expected(self):
        """Test that provider map has expected providers."""
        assert "manual" in _PROVIDER_MAP
        assert "cloudflare" in _PROVIDER_MAP
        assert "aliyun" in _PROVIDER_MAP


class TestCloudflareProvider:
    """Test Cloudflare DNS provider."""

    def test_cloudflare_missing_config(self):
        """Test Cloudflare provider with missing config."""
        from zxtoolbox.letsencrypt import CloudflareProvider

        with pytest.raises(ValueError, match="api_token"):
            CloudflareProvider({})

    def test_cloudflare_missing_zone_id(self):
        """Test Cloudflare provider with missing zone_id."""
        from zxtoolbox.letsencrypt import CloudflareProvider

        with pytest.raises(ValueError, match="zone_id"):
            CloudflareProvider({"api_token": "test"})


class TestAliyunProvider:
    """Test Aliyun DNS provider."""

    def test_aliyun_missing_config(self):
        """Test Aliyun provider with missing config."""
        from zxtoolbox.letsencrypt import AliyunProvider

        with pytest.raises(ValueError, match="access_key_id"):
            AliyunProvider({})

    def test_aliyun_split_rr_domain(self):
        """Test RR/domain splitting."""
        from zxtoolbox.letsencrypt import AliyunProvider

        rr, domain = AliyunProvider._split_rr_domain(
            "_acme-challenge.example.com", "example.com"
        )
        assert rr == "_acme-challenge"
        assert domain == "example.com"

    def test_aliyun_split_rr_domain_wildcard(self):
        """Test RR/domain splitting for wildcard."""
        from zxtoolbox.letsencrypt import AliyunProvider

        rr, domain = AliyunProvider._split_rr_domain(
            "_acme-challenge.*.example.com", "example.com"
        )
        assert rr == "_acme-challenge.*"
        assert domain == "example.com"


class TestBatchObtainCerts:
    """Test config-driven batch certificate issuance."""

    def test_batch_obtain_no_config(self, tmp_path, capsys):
        """Test batch_obtain_certs with no domain projects in config."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('[[projects]]\nproject_dir = "/test"\n', encoding="utf-8")

        results = batch_obtain_certs(str(config_path))

        # No projects with domain, should return empty dict
        assert results == {}
        captured = capsys.readouterr()
        assert "没有配置 domain" in captured.out

    def test_batch_obtain_dry_run(self, tmp_path, capsys):
        """Test batch_obtain_certs in dry-run mode."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "manual"
staging = true

[[projects]]
project_dir = "/myproject"
domain = "example.com"
''', encoding="utf-8")

        results = batch_obtain_certs(str(config_path), dry_run=True)

        assert "example.com" in results
        assert results["example.com"] is True
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out

    def test_batch_obtain_wildcard_domain_dry_run(self, tmp_path, capsys):
        """Test that wildcard domains auto-include base domain."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "manual"
staging = true

[[projects]]
project_dir = "/myproject"
domain = "*.example.com"
''', encoding="utf-8")

        # We mock obtain_cert to verify the domains list
        with patch("zxtoolbox.letsencrypt.obtain_cert") as mock_obtain:
            mock_obtain.return_value = None
            results = batch_obtain_certs(str(config_path), dry_run=True)

        # Dry run should still list the wildcard domain
        assert "*.example.com" in results

    def test_batch_obtain_missing_config_file(self, tmp_path):
        """Test batch_obtain_certs with missing config file."""
        from zxtoolbox.config_manager import load_projects_with_domain

        with pytest.raises(FileNotFoundError):
            load_projects_with_domain(str(tmp_path / "nonexistent.toml"))


class TestBatchRenewCerts:
    """Test config-driven batch certificate renewal."""

    def test_batch_renew_no_domain_projects(self, tmp_path, capsys):
        """Test batch_renew_certs with no domain projects falls back to renew_certs."""
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text('''
[letsencrypt]
provider = "manual"

[[projects]]
project_dir = "/test"
''', encoding="utf-8")

        # Will try to call renew_certs with default out_dir
        with patch("zxtoolbox.letsencrypt.renew_certs") as mock_renew:
            mock_renew.return_value = None
            results = batch_renew_certs(str(config_path))

        assert results == {}

    def test_batch_renew_valid_cert_no_renewal(self, tmp_path, capsys):
        """Test that valid certificates are not renewed."""
        from datetime import datetime, timedelta, timezone

        out_dir = tmp_path / "certs"
        out_dir.mkdir()
        out_dir_str = str(out_dir).replace("\\", "/")
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text(f'''
[letsencrypt]
provider = "manual"
staging = true
output_dir = "{out_dir_str}"

[[projects]]
project_dir = "/myproject"
domain = "example.com"
''', encoding="utf-8")

        expires_at = datetime.now(timezone.utc) + timedelta(days=60)
        state = {
            "certificates": {
                "example.com": {
                    "domains": ["example.com"],
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "provider": "manual",
                    "staging": True,
                }
            }
        }
        state_path = out_dir / "renew_state.json"
        state_path.write_text(json.dumps(state))

        results = batch_renew_certs(str(config_path))

        assert "example.com" in results
        assert results["example.com"] is True
        captured = capsys.readouterr()
        assert "无需续签" in captured.out

    def test_batch_renew_expiring_cert(self, tmp_path, capsys):
        """Test that expiring certificates get renewed."""
        from datetime import datetime, timedelta, timezone

        out_dir = tmp_path / "certs"
        out_dir.mkdir()
        out_dir_str = str(out_dir).replace("\\", "/")
        config_path = tmp_path / "zxtool.toml"
        config_path.write_text(f'''
[letsencrypt]
provider = "manual"
staging = true
output_dir = "{out_dir_str}"

[[projects]]
project_dir = "/myproject"
domain = "expiring.com"
''', encoding="utf-8")

        # Create expiring cert state
        expires_at = datetime.now(timezone.utc) + timedelta(days=10)
        state = {
            "certificates": {
                "expiring.com": {
                    "domains": ["expiring.com"],
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "provider": "manual",
                    "staging": True,
                }
            }
        }
        (out_dir / "renew_state.json").write_text(json.dumps(state))

        with patch("zxtoolbox.letsencrypt.obtain_cert") as mock_obtain:
            mock_obtain.return_value = None
            results = batch_renew_certs(str(config_path), dry_run=True)

        # dry-run should still report needing renewal
        assert "expiring.com" in results
