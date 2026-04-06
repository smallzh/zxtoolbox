"""Tests for zxtoolbox.pyopt_2fa module."""

import pytest
from unittest.mock import patch

from zxtoolbox.pyopt_2fa import parseTotpCdoe


class TestParseTotpCode:
    """Test TOTP code parsing."""

    @patch("zxtoolbox.pyopt_2fa.pyotp.TOTP")
    def test_parse_totp_code(self, mock_totp_class, capsys):
        """Test that parseTotpCdoe calls TOTP and prints the code."""
        mock_totp = mock_totp_class.return_value
        mock_totp.now.return_value = "123456"

        parseTotpCdoe("TESTSECRETKEY")

        mock_totp_class.assert_called_once_with("TESTSECRETKEY")
        mock_totp.now.assert_called_once()
        captured = capsys.readouterr()
        assert "123456" in captured.out

    @patch("zxtoolbox.pyopt_2fa.pyotp.TOTP")
    def test_parse_totp_code_different_values(self, mock_totp_class, capsys):
        """Test with a different TOTP code."""
        mock_totp = mock_totp_class.return_value
        mock_totp.now.return_value = "654321"

        parseTotpCdoe("ANOTHERKEY")

        captured = capsys.readouterr()
        assert "654321" in captured.out
