"""Tests for zxtoolbox.video_download module."""

import importlib
import subprocess
import sys

import pytest
from unittest.mock import patch, MagicMock

from zxtoolbox.video_download import _print_progress_bar


class TestPrintProgressBar:
    """Test progress bar output."""

    def test_print_progress_bar_zero(self, capsys):
        _print_progress_bar(0.0, width=10)
        captured = capsys.readouterr()
        assert "0.0%" in captured.out

    def test_print_progress_bar_full(self, capsys):
        _print_progress_bar(100.0, width=10)
        captured = capsys.readouterr()
        assert "100.0%" in captured.out

    def test_print_progress_bar_half(self, capsys):
        _print_progress_bar(50.0, width=10)
        captured = capsys.readouterr()
        assert "50.0%" in captured.out


class TestCheckFfmpeg:
    """Test ffmpeg detection."""

    def test_ffmpeg_found(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            from zxtoolbox.video_download import _check_ffmpeg

            assert _check_ffmpeg() is True

    def test_ffmpeg_not_found(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            from zxtoolbox.video_download import _check_ffmpeg

            assert _check_ffmpeg() is False

    def test_ffmpeg_timeout(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)
            from zxtoolbox.video_download import _check_ffmpeg

            assert _check_ffmpeg() is False

    def test_ffmpeg_nonzero_returncode(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            from zxtoolbox.video_download import _check_ffmpeg

            assert _check_ffmpeg() is False


class TestDownloadVideo:
    """Test video download function."""

    def _reload_module(self):
        """Reload video_download module to pick up patched yt_dlp."""
        import zxtoolbox.video_download as vd

        importlib.reload(vd)
        return vd

    def test_download_video_success(self, capsys):
        """Test successful video download."""
        mock_ydl = MagicMock()
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            result = vd.download_video("https://example.com/video")

        assert result is True
        mock_ydl.download.assert_called_once()

    def test_download_video_with_ffmpeg(self):
        """Test download with ffmpeg available."""
        mock_ydl = MagicMock()
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            with patch.object(vd, "_check_ffmpeg", return_value=True):
                result = vd.download_video("https://example.com/video")

        assert result is True
        call_args = mock_ydl_class.call_args
        opts = call_args[0][0]
        assert "postprocessors" in opts

    def test_download_video_failure(self):
        """Test failed video download."""
        mock_ydl_class = MagicMock()
        mock_ydl_class.side_effect = Exception("Download error")

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            result = vd.download_video("https://example.com/video")

        assert result is False

    def test_download_video_custom_output(self, tmp_path):
        """Test download with custom output path."""
        mock_ydl = MagicMock()
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            output = str(tmp_path / "video.mp4")
            result = vd.download_video("https://example.com/video", output_path=output)

        assert result is True
        call_args = mock_ydl_class.call_args
        opts = call_args[0][0]
        assert opts["outtmpl"] == output

    def test_download_video_no_ytdlp(self, capsys):
        """Test download when yt-dlp is not installed."""
        original = sys.modules.get("yt_dlp")
        sys.modules["yt_dlp"] = None
        try:
            vd = self._reload_module()
            result = vd.download_video("https://example.com/video")
            assert result is False
            captured = capsys.readouterr()
            assert "yt-dlp" in captured.out or "Error" in captured.out
        finally:
            if original is not None:
                sys.modules["yt_dlp"] = original
            else:
                sys.modules.pop("yt_dlp", None)
            self._reload_module()


class TestDownloadWithProgress:
    """Test download with progress bar."""

    def test_download_with_progress(self):
        """Test download_with_progress calls download_video."""
        mock_ydl = MagicMock()
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            import zxtoolbox.video_download as vd

            importlib.reload(vd)
            with patch.object(vd, "_check_ffmpeg", return_value=False):
                result = vd.download_with_progress("https://example.com/video")

        assert result is True
