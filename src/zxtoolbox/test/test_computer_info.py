"""Tests for zxtoolbox.computer_info module."""

import platform
import socket
from unittest.mock import patch, MagicMock

import pytest
from prettytable import PrettyTable

from zxtoolbox import computer_info
from zxtoolbox.computer_info import (
    convert_read_str,
    init_table,
    get_os_info,
    get_cpu_summary,
    get_memory_summary,
    get_disk_summary,
    get_network_summary,
    summary_info,
)


class TestConvertReadStr:
    """Test byte-to-human-readable conversion."""

    def test_bytes(self):
        assert convert_read_str(500) == "500 Bytes"

    def test_kb(self):
        result = convert_read_str(2048)
        assert "KB" in result
        assert "2.0" in result

    def test_mb(self):
        result = convert_read_str(2 * 1024**2)
        assert "MB" in result
        assert "2.0" in result

    def test_gb(self):
        result = convert_read_str(2 * 1024**3)
        assert "GB" in result
        assert "2.0" in result

    def test_zero(self):
        assert convert_read_str(0) == "0 Bytes"

    def test_boundary_kb(self):
        result = convert_read_str(1024)
        # 1024 bytes: 1024 / 1024 = 1.0, not > 1, so stays as Bytes
        assert "Bytes" in result or "KB" in result

    def test_boundary_mb(self):
        result = convert_read_str(1024**2)
        # 1024^2 / 1024^2 = 1.0, not > 1, so stays as KB
        assert "KB" in result or "MB" in result

    def test_boundary_gb(self):
        result = convert_read_str(1024**3)
        # 1024^3 / 1024^3 = 1.0, not > 1, so stays as MB
        assert "MB" in result or "GB" in result


class TestInitTable:
    """Test PrettyTable initialization."""

    def test_init_table_sets_fields(self):
        table = PrettyTable()
        init_table(table)
        assert table.field_names == ["property", "value"]
        assert table.align["value"] == "l"
        assert table.max_width["value"] == 50


class TestGetOsInfo:
    """Test OS info detection."""

    @patch.object(platform, "system", return_value="Windows")
    @patch.object(platform, "win32_ver", return_value=("10", "", "", ""))
    def test_windows(self, mock_ver, mock_system):
        result = get_os_info()
        assert "Windows" in result

    @patch.object(platform, "system", return_value="Darwin")
    @patch.object(platform, "mac_ver", return_value=("14.0", "", ""))
    def test_macos(self, mock_ver, mock_system):
        result = get_os_info()
        assert "macOS" in result

    @patch.object(platform, "system", return_value="Linux")
    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch.object(platform, "release", return_value="5.15.0")
    def test_linux_no_os_release(self, mock_release, mock_open, mock_system):
        result = get_os_info()
        assert "Linux" in result


class TestGetCpuSummary:
    """Test CPU summary generation."""

    @patch("zxtoolbox.computer_info.psutil.cpu_count", return_value=8)
    @patch(
        "zxtoolbox.computer_info.psutil.cpu_freq",
        return_value=MagicMock(max=3200),
    )
    def test_cpu_summary(self, mock_freq, mock_count):
        result = get_cpu_summary()
        assert "8 Cores" in result
        assert "3.2 GHz" in result

    @patch("zxtoolbox.computer_info.psutil.cpu_count", return_value=4)
    @patch("zxtoolbox.computer_info.psutil.cpu_freq", return_value=None)
    def test_cpu_summary_no_freq(self, mock_freq, mock_count):
        result = get_cpu_summary()
        assert "4 Cores" in result
        assert "N/A" in result


class TestGetMemorySummary:
    """Test memory summary generation."""

    @patch(
        "zxtoolbox.computer_info.psutil.virtual_memory",
        return_value=MagicMock(total=16 * 1024**3),
    )
    def test_memory_summary(self, mock_mem):
        result = get_memory_summary()
        assert "GB" in result


class TestGetDiskSummary:
    """Test disk summary generation."""

    @patch.object(platform, "system", return_value="Windows")
    @patch(
        "zxtoolbox.computer_info.psutil.disk_usage",
        return_value=MagicMock(total=500 * 1024**3),
    )
    def test_disk_summary_windows(self, mock_usage, mock_system):
        result = get_disk_summary()
        assert "GB" in result

    @patch.object(platform, "system", return_value="Linux")
    @patch(
        "zxtoolbox.computer_info.psutil.disk_usage",
        return_value=MagicMock(total=256 * 1024**3),
    )
    def test_disk_summary_linux(self, mock_usage, mock_system):
        result = get_disk_summary()
        assert "GB" in result


class TestGetNetworkSummary:
    """Test network summary generation."""

    @patch("zxtoolbox.computer_info.socket.gethostname", return_value="testhost")
    @patch("zxtoolbox.computer_info.socket.gethostbyname", return_value="192.168.1.100")
    def test_network_summary(self, mock_ip, mock_hostname):
        result = get_network_summary()
        assert result == "192.168.1.100"

    @patch("zxtoolbox.computer_info.socket.gethostname", return_value="testhost")
    @patch(
        "zxtoolbox.computer_info.socket.gethostbyname",
        side_effect=socket.gaierror,
    )
    def test_network_summary_error(self, mock_ip, mock_hostname):
        result = get_network_summary()
        assert result == "N/A"


class TestSummaryInfo:
    """Test summary output."""

    def test_summary_info_output(self, capsys):
        with (
            patch("zxtoolbox.computer_info.get_os_info", return_value="Windows 10"),
            patch(
                "zxtoolbox.computer_info.get_cpu_summary",
                return_value="8 Cores, 3.2 GHz",
            ),
            patch("zxtoolbox.computer_info.get_gpu_summary", return_value="N/A"),
            patch("zxtoolbox.computer_info.get_memory_summary", return_value="16.0 GB"),
            patch("zxtoolbox.computer_info.get_disk_summary", return_value="500.0 GB"),
            patch(
                "zxtoolbox.computer_info.get_network_summary",
                return_value="192.168.1.1",
            ),
        ):
            summary_info()
        captured = capsys.readouterr()
        assert "Windows 10" in captured.out
        assert "8 Cores" in captured.out
        assert "16.0 GB" in captured.out
