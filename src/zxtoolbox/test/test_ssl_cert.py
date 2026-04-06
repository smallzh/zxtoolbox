"""Tests for zxtoolbox.ssl_cert module."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from zxtoolbox.ssl_cert import (
    init,
    generate_root,
    _run,
    _write_ca_cnf,
    DEFAULT_COUNTRY,
    DEFAULT_STATE,
    DEFAULT_LOCALITY,
    DEFAULT_ORG,
    DEFAULT_ROOT_CN,
    DEFAULT_ROOT_DAYS,
    DEFAULT_CERT_DAYS,
    RSA_BITS,
)


class TestRun:
    """Test the _run helper function."""

    @patch("zxtoolbox.ssl_cert.subprocess.run")
    def test_run_success(self, mock_run):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = _run(["echo", "test"])
        assert result.returncode == 0

    @patch("zxtoolbox.ssl_cert.subprocess.run")
    def test_run_failure(self, mock_run, capsys):
        """Test command failure raises RuntimeError."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        with pytest.raises(RuntimeError):
            _run(["false"])


class TestWriteCaCnf:
    """Test CA config file generation."""

    def test_write_ca_cnf(self, tmp_path):
        """Test writing ca.cnf file."""
        cnf_path = _write_ca_cnf(tmp_path)
        assert cnf_path.exists()
        content = cnf_path.read_text()
        assert DEFAULT_COUNTRY in content
        assert DEFAULT_STATE in content
        assert DEFAULT_ORG in content
        assert str(tmp_path / "newcerts") in content


class TestInit:
    """Test output directory initialization."""

    def test_init_new_directory(self, tmp_path):
        """Test initializing a new directory."""
        out_dir = tmp_path / "out"
        init(out_dir)

        assert (out_dir / "newcerts").exists()
        assert (out_dir / "index.txt").exists()
        assert (out_dir / "index.txt.attr").exists()
        assert (out_dir / "serial").exists()
        assert (out_dir / "ca.cnf").exists()

        # Check serial file content
        serial = (out_dir / "serial").read_text()
        assert serial.strip() == "1000"

    def test_init_existing_directory(self, tmp_path):
        """Test initializing overwrites existing directory."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "old_file.txt").write_text("old")

        init(out_dir)

        assert not (out_dir / "old_file.txt").exists()
        assert (out_dir / "newcerts").exists()
        assert (out_dir / "ca.cnf").exists()


class TestGenerateRoot:
    """Test Root CA certificate generation."""

    @patch("zxtoolbox.ssl_cert._run")
    @patch("zxtoolbox.ssl_cert._write_ca_cnf")
    def test_generate_root_success(self, mock_write_cnf, mock_run, tmp_path):
        """Test successful Root CA generation."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "index.txt").touch()

        result = generate_root(out_dir)

        assert result is True
        # Should call _run twice: once for req, once for genrsa
        assert mock_run.call_count == 2

        # Verify the req command arguments
        req_call = mock_run.call_args_list[0]
        req_args = req_call[0][0]
        assert "openssl" in req_args
        assert "req" in req_args
        assert "-x509" in req_args
        assert str(DEFAULT_ROOT_DAYS) in req_args
        assert DEFAULT_ROOT_CN in " ".join(req_args)

        # Verify the genrsa command
        genrsa_call = mock_run.call_args_list[1]
        genrsa_args = genrsa_call[0][0]
        assert "genrsa" in genrsa_args
        assert str(RSA_BITS) in genrsa_args

    @patch("zxtoolbox.ssl_cert._run")
    def test_generate_root_already_exists(self, mock_run, tmp_path, capsys):
        """Test skipping when root cert already exists."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "root.crt").touch()

        result = generate_root(out_dir)

        assert result is False
        mock_run.assert_not_called()

    @patch("zxtoolbox.ssl_cert._run")
    def test_generate_root_force_regenerate(self, mock_run, tmp_path):
        """Test force regeneration of root cert."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "root.crt").touch()
        (out_dir / "index.txt").touch()

        result = generate_root(out_dir, force=True)

        assert result is True
        assert mock_run.call_count == 2

    @patch("zxtoolbox.ssl_cert._run")
    @patch("zxtoolbox.ssl_cert.init")
    def test_generate_root_auto_init(self, mock_init, mock_run, tmp_path):
        """Test auto-init when index.txt is missing."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        generate_root(out_dir)

        mock_init.assert_called_once_with(out_dir)
