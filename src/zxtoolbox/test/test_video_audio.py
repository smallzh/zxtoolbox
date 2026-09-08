"""Tests for zxtoolbox.video_audio module."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import zxtoolbox.video_audio as vd_extract


class TestCheckFfmpeg:
    """Test ffmpeg detection."""

    def test_ffmpeg_found(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            from zxtoolbox.video_audio import _check_ffmpeg

            assert _check_ffmpeg() is True

    def test_ffmpeg_not_found(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            from zxtoolbox.video_audio import _check_ffmpeg

            assert _check_ffmpeg() is False

    def test_ffmpeg_timeout(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)
            from zxtoolbox.video_audio import _check_ffmpeg

            assert _check_ffmpeg() is False

    def test_ffmpeg_nonzero_returncode(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            from zxtoolbox.video_audio import _check_ffmpeg

            assert _check_ffmpeg() is False


class TestExtractAudio:
    """Test audio extraction via ffmpeg."""

    def _make_video_file(self, tmp_path: Path, name: str = "movie.mp4") -> Path:
        video = tmp_path / name
        video.write_bytes(b"fake video content")
        return video

    def test_extract_audio_success_mp3(self, tmp_path, capsys):
        video = self._make_video_file(tmp_path)
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = vd_extract.extract_audio(str(video))

        assert result is True
        command = mock_run.call_args[0][0]
        assert command[0] == "ffmpeg"
        assert "-vn" in command
        assert "libmp3lame" in command
        assert "-b:a" in command
        assert command[command.index("-b:a") + 1] == "192k"
        assert command[-1] == str(tmp_path / "movie.mp3")
        assert "successfully" in capsys.readouterr().out

    def test_extract_audio_decodes_subprocess_as_utf8(self, tmp_path):
        """Regression: ffmpeg output must not be decoded with the Windows
        locale codec (GBK), which crashed with UnicodeDecodeError in the
        subprocess reader thread on Chinese Windows."""
        video = self._make_video_file(tmp_path)
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert vd_extract.extract_audio(str(video)) is True

        kwargs = mock_run.call_args[1]
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"

    def test_extract_audio_default_output_uses_source_stem(self, tmp_path):
        video = self._make_video_file(tmp_path, "my.video.mkv")
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert vd_extract.extract_audio(str(video)) is True

        command = mock_run.call_args[0][0]
        assert command[-1] == str(tmp_path / "my.video.mp3")

    def test_extract_audio_output_directory(self, tmp_path):
        video = self._make_video_file(tmp_path)
        out_dir = tmp_path / "audios"
        out_dir.mkdir()
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert vd_extract.extract_audio(str(video), output_path=str(out_dir)) is True

        command = mock_run.call_args[0][0]
        assert command[-1] == str(out_dir / "movie.mp3")

    def test_extract_audio_output_file_forces_extension(self, tmp_path):
        video = self._make_video_file(tmp_path)
        output = tmp_path / "sound.m4a"
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert vd_extract.extract_audio(str(video), output_path=str(output)) is True

        command = mock_run.call_args[0][0]
        assert command[-1] == str(tmp_path / "sound.mp3")

    def test_extract_audio_wav_skips_bitrate(self, tmp_path):
        video = self._make_video_file(tmp_path)
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert vd_extract.extract_audio(str(video), audio_format="wav") is True

        command = mock_run.call_args[0][0]
        assert "pcm_s16le" in command
        assert "-b:a" not in command

    def test_extract_audio_input_not_found(self, tmp_path, capsys):
        result = vd_extract.extract_audio(str(tmp_path / "missing.mp4"))
        assert result is False
        assert "not found" in capsys.readouterr().out

    def test_extract_audio_unsupported_format(self, tmp_path, capsys):
        video = self._make_video_file(tmp_path)
        result = vd_extract.extract_audio(str(video), audio_format="wma")
        assert result is False
        captured = capsys.readouterr().out
        assert "unsupported audio format" in captured
        assert "mp3" in captured

    def test_extract_audio_no_ffmpeg(self, tmp_path, capsys):
        video = self._make_video_file(tmp_path)
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=False):
            result = vd_extract.extract_audio(str(video))

        assert result is False
        assert "ffmpeg not found" in capsys.readouterr().out

    def test_extract_audio_ffmpeg_failure(self, tmp_path, capsys):
        video = self._make_video_file(tmp_path)
        with patch("zxtoolbox.video_audio._check_ffmpeg", return_value=True), \
             patch("zxtoolbox.video_audio.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="line1\nline2\nInvalid data\n")

        assert vd_extract.extract_audio(str(video)) is False
        assert "Invalid data" in capsys.readouterr().out
