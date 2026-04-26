"""Tests for zxtoolbox.http_server module."""

from unittest.mock import MagicMock, patch

from zxtoolbox.http_server import serve_directory


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
        assert "静态目录" in captured.out
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
        assert "目录不存在" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer")
    def test_serve_directory_rejects_file(self, mock_server_cls, tmp_path, capsys):
        """Test serving a file path instead of a directory."""
        file_path = tmp_path / "index.html"
        file_path.write_text("hello", encoding="utf-8")

        serve_directory(file_path)

        mock_server_cls.assert_not_called()
        captured = capsys.readouterr()
        assert "目标不是目录" in captured.out

    @patch("zxtoolbox.http_server.ThreadingHTTPServer", side_effect=OSError("port in use"))
    def test_serve_directory_start_failure(self, mock_server_cls, tmp_path, capsys):
        """Test reporting startup failure."""
        serve_directory(tmp_path)

        mock_server_cls.assert_called_once()
        captured = capsys.readouterr()
        assert "HTTP 服务启动失败" in captured.out
