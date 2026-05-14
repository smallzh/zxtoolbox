"""Tests for zxtoolbox.video_download module."""

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from zxtoolbox.video_download import (
    _print_progress_bar,
    _resolve_output_dir,
    _resolve_output,
    _with_generic_impersonation,
)


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

    def test_download_video_custom_output(self):
        """Test download with custom output path."""
        mock_ydl = MagicMock()
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            output_dir = Path(".pytest_temp") / "video_download_custom_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            output = str(output_dir / "video.mp4")
            result = vd.download_video("https://example.com/video", output_path=output)

        assert result is True
        call_args = mock_ydl_class.call_args
        opts = call_args[0][0]
        assert opts["outtmpl"] == output

    def test_download_video_directory_output(self):
        """Test download when output points to a directory."""
        mock_ydl = MagicMock()
        mock_ydl_class = MagicMock()
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            output_dir_path = Path(".pytest_temp") / "video_download_dir_output"
            output_dir_path.mkdir(parents=True, exist_ok=True)
            output_dir = str(output_dir_path)
            result = vd.download_video("https://example.com/video", output_path=output_dir)

        assert result is True
        opts = mock_ydl_class.call_args[0][0]
        assert opts["outtmpl"] == str(Path(output_dir) / "%(title)s.%(ext)s")

    def test_download_video_retries_with_impersonation(self):
        """Test Cloudflare 403 triggers a retry with impersonation."""
        download_error = Exception(
            "ERROR: [generic] Got HTTP Error 403 caused by Cloudflare anti-bot challenge; "
            "try again with --extractor-args \"generic:impersonate\""
        )
        mock_ydl = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = MagicMock(return_value=mock_ydl)
        mock_context_manager.__exit__ = MagicMock(return_value=False)
        mutated_opts = []

        def ydl_factory(opts):
            mutated_opts.append(opts)
            if len(mutated_opts) == 1:
                opts["outtmpl"] = {"default": "%(title)s.%(ext)s"}
                raise download_error
            return mock_context_manager

        mock_ydl_class = MagicMock(side_effect=ydl_factory)

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            result = vd.download_video("https://example.com/video")

        assert result is True
        assert mock_ydl_class.call_count == 2
        retry_opts = mock_ydl_class.call_args_list[1][0][0]
        assert retry_opts["extractor_args"]["generic"]["impersonate"] == ["chrome"]
        assert retry_opts["outtmpl"] == "%(title)s.%(ext)s"

    def test_download_video_missing_impersonation_dependency(self, capsys):
        """Test user-facing hint when curl-cffi is missing."""
        download_error = Exception(
            "Cloudflare anti-bot challenge detected; try again with generic:impersonate"
        )
        retry_error = Exception("ModuleNotFoundError: No module named 'curl_cffi'")
        mock_ydl_class = MagicMock(side_effect=[download_error, retry_error])

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            result = vd.download_video("https://example.com/video")

        assert result is False
        captured = capsys.readouterr()
        assert "curl-cffi" in captured.out

    def test_download_video_unsupported_impersonation_dependency(self, capsys):
        """Test user-facing hint when curl-cffi version is unsupported by yt-dlp."""
        download_error = Exception(
            "Cloudflare anti-bot challenge detected; try again with generic:impersonate"
        )
        retry_error = Exception(
            "ImportError: Only curl_cffi versions 0.5.10 and 0.10.x through 0.14.x are supported"
        )
        mock_ydl_class = MagicMock(side_effect=[download_error, retry_error])

        with patch.dict("sys.modules", {"yt_dlp": MagicMock(YoutubeDL=mock_ydl_class)}):
            vd = self._reload_module()
            result = vd.download_video("https://example.com/video")

        assert result is False
        captured = capsys.readouterr()
        assert "not compatible" in captured.out

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


class TestVideoDownloadHelpers:
    """Test helper utilities."""

    def test_resolve_output_file(self):
        output_dir = Path(".pytest_temp") / "resolve_output_file"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = str(output_dir / "video.mp4")
        outtmpl, outdir = _resolve_output(output)
        assert outtmpl == output
        assert outdir == output_dir

    def test_resolve_output_directory(self):
        output_dir = Path(".pytest_temp") / "resolve_output_directory"
        output_dir.mkdir(parents=True, exist_ok=True)
        outtmpl, outdir = _resolve_output(str(output_dir))
        assert outtmpl == str(output_dir / "%(title)s.%(ext)s")
        assert outdir == output_dir

    def test_with_generic_impersonation_preserves_other_options(self):
        opts = {"quiet": False, "extractor_args": {"youtube": {"player_client": ["web"]}}}
        retry_opts = _with_generic_impersonation(opts)
        assert retry_opts["quiet"] is False
        assert retry_opts["extractor_args"]["youtube"]["player_client"] == ["web"]
        assert retry_opts["extractor_args"]["generic"]["impersonate"] == ["chrome"]

    def test_resolve_output_dir_from_outtmpl_dict(self):
        output_dir = _resolve_output_dir({"default": "videos/%(title)s.%(ext)s"})
        assert output_dir == Path("videos")


def teardown_module(_module):
    """Clean temporary directories created by this test module."""
    shutil.rmtree(".pytest_temp", ignore_errors=True)
