"""Tests for zxtoolbox.http_server module."""

import base64
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zxtoolbox.http_server import (
    HTTP_VIDEO_PAGE_CSS_ROUTE,
    HTTP_VIDEO_PAGE_JS_ROUTE,
    HTTP_VIDEO_SCREENSHOT_API_ROUTE,
    HTTP_VIDEO_XGPLAYER_CSS_ROUTE,
    HTTP_VIDEO_XGPLAYER_JS_ROUTE,
    VideoPlayerRequestHandler,
    _build_video_page_html,
    _parse_byte_range,
    _resolve_video_file,
    _save_screenshot_data_url,
    serve_directory,
    serve_video,
)


class TestServeDirectory:
    """Test static file HTTP serving."""

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_directory_default(self, mock_server_cls, tmp_path, capsys):
        """Test serving a directory with default host and port."""
        mock_server = MagicMock()
        mock_server.server_address = ("127.0.0.1", 8000)
        mock_server.serve_forever.side_effect = KeyboardInterrupt
        mock_server_cls.return_value = mock_server

        serve_directory(str(tmp_path))

        mock_server_cls.assert_called_once()
        server_address, handler_class = mock_server_cls.call_args[0]
        assert server_address == ("127.0.0.1", 8000)
        assert handler_class.keywords["directory"] == str(tmp_path.resolve())
        mock_server.serve_forever.assert_called_once()
        mock_server.server_close.assert_called_once()

        captured = capsys.readouterr()
        assert "Serving directory:" in captured.out
        assert "127.0.0.1:8000" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_directory_custom_host_and_port(self, mock_server_cls, tmp_path):
        """Test serving a directory with custom host and port."""
        mock_server = MagicMock()
        mock_server.server_address = ("0.0.0.0", 9000)
        mock_server.serve_forever.side_effect = KeyboardInterrupt
        mock_server_cls.return_value = mock_server

        serve_directory(tmp_path, host="0.0.0.0", port=9000)

        server_address, handler_class = mock_server_cls.call_args[0]
        assert server_address == ("0.0.0.0", 9000)
        assert handler_class.keywords["directory"] == str(tmp_path.resolve())

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_directory_missing_path(self, mock_server_cls, tmp_path, capsys):
        """Test serving a non-existent directory."""
        serve_directory(tmp_path / "missing")

        mock_server_cls.assert_not_called()
        captured = capsys.readouterr()
        assert "directory does not exist" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_directory_rejects_file(self, mock_server_cls, tmp_path, capsys):
        """Test serving a file path instead of a directory."""
        file_path = tmp_path / "index.html"
        file_path.write_text("hello", encoding="utf-8")

        serve_directory(file_path)

        mock_server_cls.assert_not_called()
        captured = capsys.readouterr()
        assert "target is not a directory" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer", side_effect=OSError("port in use"))
    def test_serve_directory_start_failure(self, mock_server_cls, tmp_path, capsys):
        """Test reporting startup failure."""
        serve_directory(tmp_path)

        mock_server_cls.assert_called_once()
        captured = capsys.readouterr()
        assert "failed to start HTTP server" in captured.out


class TestServeVideo:
    """Test HTTP video serving."""

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_video_default_selects_single_mp4(self, mock_server_cls, tmp_path, capsys):
        """Test serving the only MP4 file in one directory."""
        video_path = tmp_path / "demo.mp4"
        video_path.write_bytes(b"fake")

        mock_server = MagicMock()
        mock_server.server_address = ("127.0.0.1", 8000)
        mock_server.serve_forever.side_effect = KeyboardInterrupt
        mock_server_cls.return_value = mock_server

        serve_video(tmp_path)

        mock_server_cls.assert_called_once()
        server_address, handler_class = mock_server_cls.call_args[0]
        assert server_address == ("127.0.0.1", 8000)
        assert handler_class.keywords["directory"] == str(tmp_path.resolve())
        assert "demo.mp4" in handler_class.keywords["page_html"]
        mock_server.server_close.assert_called_once()

        captured = capsys.readouterr()
        assert "Serving video directory:" in captured.out
        assert "Video file: demo.mp4" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_video_with_explicit_file(self, mock_server_cls, tmp_path):
        """Test serving an explicitly selected MP4 file."""
        (tmp_path / "a.mp4").write_bytes(b"a")
        chosen = tmp_path / "b.mp4"
        chosen.write_bytes(b"b")

        mock_server = MagicMock()
        mock_server.server_address = ("127.0.0.1", 9000)
        mock_server.serve_forever.side_effect = KeyboardInterrupt
        mock_server_cls.return_value = mock_server

        serve_video(tmp_path, video_file="b.mp4", host="0.0.0.0", port=9000, title="My Video")

        server_address, handler_class = mock_server_cls.call_args[0]
        assert server_address == ("0.0.0.0", 9000)
        assert "My Video" in handler_class.keywords["page_html"]
        assert "/b.mp4" in handler_class.keywords["page_html"]

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_video_requires_one_mp4_without_file_option(self, mock_server_cls, tmp_path, capsys):
        """Test rejecting ambiguous directories with multiple MP4 files."""
        (tmp_path / "a.mp4").write_bytes(b"a")
        (tmp_path / "b.mp4").write_bytes(b"b")

        serve_video(tmp_path)

        mock_server_cls.assert_not_called()
        captured = capsys.readouterr()
        assert "multiple MP4 files found" in captured.out
        assert "a.mp4" in captured.out
        assert "b.mp4" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_video_reports_missing_mp4(self, mock_server_cls, tmp_path, capsys):
        """Test rejecting directories without MP4 files."""
        (tmp_path / "note.txt").write_text("hello", encoding="utf-8")

        serve_video(tmp_path)

        mock_server_cls.assert_not_called()
        captured = capsys.readouterr()
        assert "no MP4 file found" in captured.out


def test_resolve_video_file_rejects_outside_directory(tmp_path, capsys):
    """Video file must stay inside the served directory."""
    outside = tmp_path.parent / "outside.mp4"
    outside.write_bytes(b"fake")

    resolved = _resolve_video_file(tmp_path, outside)

    assert resolved is None
    captured = capsys.readouterr()
    assert "must stay within the served directory" in captured.out


def test_build_video_page_html_contains_local_assets(tmp_path):
    """Generated page should reference vendored local assets only."""
    video_path = tmp_path / "demo.mp4"
    video_path.write_bytes(b"fake")

    page = _build_video_page_html(
        video_path=video_path,
        video_url_path="/demo.mp4",
        title="Demo",
    )

    assert HTTP_VIDEO_XGPLAYER_CSS_ROUTE in page
    assert HTTP_VIDEO_XGPLAYER_JS_ROUTE in page
    assert HTTP_VIDEO_PAGE_CSS_ROUTE in page
    assert HTTP_VIDEO_PAGE_JS_ROUTE in page
    assert "cdn" not in page.lower()
    marker = "window.__ZXTOOL_HTTP_VIDEO__ = "
    payload = page.split(marker, 1)[1].split(";", 1)[0].strip()
    config = json.loads(payload)
    assert config["videoUrl"] == "/demo.mp4"
    assert config["videoName"] == "demo.mp4"
    assert config["screenshotApiUrl"] == HTTP_VIDEO_SCREENSHOT_API_ROUTE


def test_save_screenshot_data_url_writes_png(tmp_path):
    """PNG screenshot data URLs should be saved into the target directory."""
    data_url = "data:image/png;base64," + base64.b64encode(b"pngdata").decode("ascii")

    output_path = _save_screenshot_data_url(
        screenshot_dir=tmp_path,
        screenshot_base_name="demo",
        data_url=data_url,
    )

    assert output_path.parent == tmp_path.resolve()
    assert output_path.name.startswith("demo-screenshot-")
    assert output_path.suffix == ".png"
    assert output_path.read_bytes() == b"pngdata"


def test_save_screenshot_data_url_rejects_non_png(tmp_path):
    """Only PNG data URLs should be accepted."""
    with pytest.raises(ValueError, match="only PNG"):
        _save_screenshot_data_url(
            screenshot_dir=tmp_path,
            screenshot_base_name="demo",
            data_url="data:image/jpeg;base64,abcd",
        )


@pytest.mark.parametrize(
    ("range_header", "file_size", "expected"),
    [
        ("bytes=0-9", 100, (0, 9)),
        ("bytes=10-", 100, (10, 99)),
        ("bytes=-10", 100, (90, 99)),
        ("bytes=0-999", 100, (0, 99)),
    ],
)
def test_parse_byte_range_valid(range_header, file_size, expected):
    """Byte ranges should be parsed into inclusive bounds."""
    assert _parse_byte_range(range_header, file_size) == expected


@pytest.mark.parametrize(
    ("range_header", "file_size"),
    [
        ("items=0-9", 100),
        ("bytes=90-10", 100),
        ("bytes=100-110", 100),
        ("bytes=", 100),
        ("bytes=1-2,4-5", 100),
    ],
)
def test_parse_byte_range_invalid(range_header, file_size):
    """Invalid ranges should be rejected."""
    assert _parse_byte_range(range_header, file_size) is None


def test_video_player_request_handler_serves_root_page(tmp_path):
    """Custom video handler should serve the generated root page."""
    request = object.__new__(VideoPlayerRequestHandler)
    request.path = "/"
    request.headers = {}
    request.wfile = BytesIO()
    request.send_response = MagicMock()
    request.send_header = MagicMock()
    request.end_headers = MagicMock()
    request._page_html = b"<html>demo</html>"

    request._dispatch_request(head_only=False)

    request.send_response.assert_called_once_with(200)
    assert request.wfile.getvalue() == b"<html>demo</html>"


def test_video_player_request_handler_head_skips_body(tmp_path):
    """HEAD requests should send headers without a body."""
    request = object.__new__(VideoPlayerRequestHandler)
    request.path = "/"
    request.headers = {}
    request.wfile = BytesIO()
    request.send_response = MagicMock()
    request.send_header = MagicMock()
    request.end_headers = MagicMock()
    request._page_html = b"<html>demo</html>"

    request._dispatch_request(head_only=True)

    request.send_response.assert_called_once_with(200)
    assert request.wfile.getvalue() == b""


def test_video_player_request_handler_uploads_screenshot(tmp_path):
    """Screenshot API should save one PNG into the video directory."""
    payload = {
        "imageDataUrl": "data:image/png;base64," + base64.b64encode(b"image").decode("ascii"),
    }
    body = json.dumps(payload).encode("utf-8")

    request = object.__new__(VideoPlayerRequestHandler)
    request.path = HTTP_VIDEO_SCREENSHOT_API_ROUTE
    request.headers = {"Content-Length": str(len(body))}
    request.rfile = BytesIO(body)
    request.wfile = BytesIO()
    request.send_response = MagicMock()
    request.send_header = MagicMock()
    request.end_headers = MagicMock()
    request._screenshot_dir = tmp_path
    request._screenshot_base_name = "demo"

    request._handle_screenshot_upload()

    request.send_response.assert_called_once_with(200)
    response = json.loads(request.wfile.getvalue().decode("utf-8"))
    assert response["ok"] is True
    saved_path = Path(response["filePath"])
    assert saved_path.exists()
    assert saved_path.parent == tmp_path.resolve()
    assert saved_path.read_bytes() == b"image"
