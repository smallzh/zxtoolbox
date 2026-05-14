"""Static file HTTP server helpers."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from functools import lru_cache, partial
import html
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit


HTTP_VIDEO_PAGE_CSS_ROUTE = "/__zxtool_assets/http_video/player.css"
HTTP_VIDEO_PAGE_JS_ROUTE = "/__zxtool_assets/http_video/player.js"
HTTP_VIDEO_XGPLAYER_CSS_ROUTE = "/__zxtool_assets/xgplayer/index.min.css"
HTTP_VIDEO_XGPLAYER_JS_ROUTE = "/__zxtool_assets/xgplayer/index.min.js"
HTTP_VIDEO_SCREENSHOT_API_ROUTE = "/__zxtool_api/http_video/screenshot"
HTTP_VIDEO_ALLOWED_SUFFIXES = {".mp4"}
HTTP_VIDEO_ASSET_ROUTES: dict[str, tuple[str, tuple[str, ...]]] = {
    HTTP_VIDEO_PAGE_CSS_ROUTE: (
        "text/css; charset=utf-8",
        ("assets", "http_video", "player.css"),
    ),
    HTTP_VIDEO_PAGE_JS_ROUTE: (
        "text/javascript; charset=utf-8",
        ("assets", "http_video", "player.js"),
    ),
    HTTP_VIDEO_XGPLAYER_CSS_ROUTE: (
        "text/css; charset=utf-8",
        ("assets", "xgplayer", "index.min.css"),
    ),
    HTTP_VIDEO_XGPLAYER_JS_ROUTE: (
        "text/javascript; charset=utf-8",
        ("assets", "xgplayer", "index.min.js"),
    ),
}


class VideoPlayerRequestHandler(SimpleHTTPRequestHandler):
    """Serve a generated video player page plus one directory of files."""

    def __init__(
        self,
        *args: object,
        directory: str | None = None,
        page_html: str,
        screenshot_dir: str,
        screenshot_base_name: str,
        **kwargs: object,
    ) -> None:
        self._page_html = page_html.encode("utf-8")
        self._byte_range: tuple[int, int] | None = None
        self._screenshot_dir = Path(screenshot_dir)
        self._screenshot_base_name = screenshot_base_name
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        """Handle one GET request."""
        self._dispatch_request(head_only=False)

    def do_HEAD(self) -> None:  # noqa: N802
        """Handle one HEAD request."""
        self._dispatch_request(head_only=True)

    def do_POST(self) -> None:  # noqa: N802
        """Handle one POST request."""
        request_path = urlsplit(self.path).path or "/"
        if request_path == HTTP_VIDEO_SCREENSHOT_API_ROUTE:
            self._handle_screenshot_upload()
            return

        self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    def _dispatch_request(self, *, head_only: bool) -> None:
        request_path = urlsplit(self.path).path or "/"

        if request_path in {"/", "/index.html"}:
            self._send_bytes(
                self._page_html,
                "text/html; charset=utf-8",
                head_only=head_only,
            )
            return

        asset = HTTP_VIDEO_ASSET_ROUTES.get(request_path)
        if asset is not None:
            content_type, resource_path = asset
            try:
                content = _read_bundled_asset(resource_path)
            except FileNotFoundError:
                self.send_error(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    f"Bundled asset not found: {'/'.join(resource_path)}",
                )
                return

            self._send_bytes(content, content_type, head_only=head_only)
            return

        if head_only:
            super().do_HEAD()
        else:
            super().do_GET()

    def _send_bytes(self, content: bytes, content_type: str, *, head_only: bool) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        if not head_only:
            self.wfile.write(content)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _handle_screenshot_upload(self) -> None:
        content_length_header = self.headers.get("Content-Length")
        if content_length_header is None:
            self._send_json(
                {"ok": False, "message": "missing Content-Length"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            content_length = int(content_length_header)
        except ValueError:
            self._send_json(
                {"ok": False, "message": "invalid Content-Length"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        if content_length <= 0:
            self._send_json(
                {"ok": False, "message": "empty request body"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(
                {"ok": False, "message": "request body must be valid JSON"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        data_url = payload.get("imageDataUrl")
        if not isinstance(data_url, str) or not data_url:
            self._send_json(
                {"ok": False, "message": "imageDataUrl is required"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            output_path = _save_screenshot_data_url(
                screenshot_dir=self._screenshot_dir,
                screenshot_base_name=self._screenshot_base_name,
                data_url=data_url,
            )
        except ValueError as exc:
            self._send_json(
                {"ok": False, "message": str(exc)},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        except OSError as exc:
            self._send_json(
                {"ok": False, "message": f"failed to save screenshot: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(
            {
                "ok": True,
                "message": "screenshot saved",
                "fileName": output_path.name,
                "filePath": str(output_path),
            }
        )

    def send_head(self):  # type: ignore[override]
        """Send headers for static files with optional byte-range support."""
        self._byte_range = None
        path = self.translate_path(self.path)

        if os.path.isdir(path):
            return super().send_head()

        try:
            file_handle = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            stat_result = os.fstat(file_handle.fileno())
            file_size = stat_result.st_size
            content_type = self.guess_type(path)
            range_header = self.headers.get("Range")

            if range_header:
                byte_range = _parse_byte_range(range_header, file_size)
                if byte_range is None:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    file_handle.close()
                    return None

                start, end = byte_range
                self._byte_range = byte_range
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", content_type)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(end - start + 1))
                self.send_header("Last-Modified", self.date_time_string(stat_result.st_mtime))
                self.end_headers()
                file_handle.seek(start)
                return file_handle

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Last-Modified", self.date_time_string(stat_result.st_mtime))
            self.end_headers()
            return file_handle
        except Exception:
            file_handle.close()
            raise

    def copyfile(self, source, outputfile) -> None:  # type: ignore[override]
        """Copy one file object to the response stream."""
        if self._byte_range is None:
            super().copyfile(source, outputfile)
            return

        start, end = self._byte_range
        remaining = end - start + 1
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def serve_directory(
    directory: str | Path = ".",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Start a static file HTTP server for one directory."""
    directory_path = _resolve_directory_path(directory)
    if directory_path is None:
        return

    handler_class = partial(
        SimpleHTTPRequestHandler,
        directory=str(directory_path),
    )
    _run_http_server(
        handler_class=handler_class,
        host=host,
        port=port,
        startup_lines=[
            f"Serving directory: {directory_path}",
        ],
    )


def serve_video(
    directory: str | Path = ".",
    video_file: str | Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    title: str | None = None,
) -> None:
    """Start an HTTP video player page for one MP4 file in a directory."""
    directory_path = _resolve_directory_path(directory)
    if directory_path is None:
        return

    resolved_video = _resolve_video_file(directory_path, video_file)
    if resolved_video is None:
        return

    video_relative_path = resolved_video.relative_to(directory_path).as_posix()
    video_url_path = "/" + quote(video_relative_path, safe="/")
    page_title = (title or resolved_video.stem).strip() or resolved_video.stem
    page_html = _build_video_page_html(
        video_path=resolved_video,
        video_url_path=video_url_path,
        title=page_title,
    )

    handler_class = partial(
        VideoPlayerRequestHandler,
        directory=str(directory_path),
        page_html=page_html,
        screenshot_dir=str(resolved_video.parent),
        screenshot_base_name=resolved_video.stem,
    )
    _run_http_server(
        handler_class=handler_class,
        host=host,
        port=port,
        startup_lines=[
            f"Serving video directory: {directory_path}",
            f"Video file: {resolved_video.name}",
            "Video player page: /",
            f"Direct video URL: {video_url_path}",
        ],
    )


def _run_http_server(
    handler_class: type[SimpleHTTPRequestHandler] | partial[SimpleHTTPRequestHandler],
    host: str,
    port: int,
    startup_lines: list[str],
) -> None:
    """Start one threaded HTTP server and print startup details."""
    try:
        httpd = ThreadingHTTPServer((host, port), handler_class)
    except OSError as exc:
        print(f"[ERROR] failed to start HTTP server: {exc}")
        return

    try:
        bound_host, bound_port = httpd.server_address[:2]
        display_host = host or bound_host

        for line in startup_lines:
            print(line)
        print(f"Server address: http://{display_host}:{bound_port}")
        print("Press Ctrl+C to stop the server")

        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] HTTP server stopped")
    finally:
        httpd.server_close()


def _resolve_directory_path(directory: str | Path) -> Path | None:
    """Resolve and validate one target directory path."""
    directory_path = Path(directory).resolve()

    if not directory_path.exists():
        print(f"[ERROR] directory does not exist: {directory_path}")
        return None

    if not directory_path.is_dir():
        print(f"[ERROR] target is not a directory: {directory_path}")
        return None

    return directory_path


def _resolve_video_file(directory_path: Path, video_file: str | Path | None) -> Path | None:
    """Resolve the one MP4 file to serve from a directory."""
    if video_file is None:
        mp4_files = sorted(
            [
                candidate.resolve()
                for candidate in directory_path.iterdir()
                if candidate.is_file() and candidate.suffix.lower() in HTTP_VIDEO_ALLOWED_SUFFIXES
            ],
            key=lambda item: item.name.lower(),
        )

        if not mp4_files:
            print(f"[ERROR] no MP4 file found in directory: {directory_path}")
            return None

        if len(mp4_files) > 1:
            print("[ERROR] multiple MP4 files found; use `--file` to choose one:")
            for item in mp4_files:
                print(f"  - {item.name}")
            return None

        return mp4_files[0]

    candidate = Path(video_file).expanduser()
    if not candidate.is_absolute():
        candidate = (directory_path / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.exists():
        print(f"[ERROR] video file does not exist: {candidate}")
        return None

    if not candidate.is_file():
        print(f"[ERROR] video target is not a file: {candidate}")
        return None

    try:
        candidate.relative_to(directory_path)
    except ValueError:
        print(f"[ERROR] video file must stay within the served directory: {candidate}")
        return None

    if candidate.suffix.lower() not in HTTP_VIDEO_ALLOWED_SUFFIXES:
        print(f"[ERROR] video file must be an MP4 file: {candidate}")
        return None

    return candidate


def _build_video_page_html(video_path: Path, video_url_path: str, title: str) -> str:
    """Build the HTTP video player page."""
    page_config = {
        "videoUrl": video_url_path,
        "videoName": video_path.name,
        "pageTitle": title,
        "screenshotBaseName": video_path.stem,
        "screenshotApiUrl": HTTP_VIDEO_SCREENSHOT_API_ROUTE,
    }
    config_json = _serialize_script_json(page_config)
    safe_title = html.escape(title)
    safe_video_name = html.escape(video_path.name)
    safe_video_url = html.escape(video_url_path, quote=True)

    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{safe_title}</title>",
            f'  <link rel="stylesheet" href="{HTTP_VIDEO_XGPLAYER_CSS_ROUTE}">',
            f'  <link rel="stylesheet" href="{HTTP_VIDEO_PAGE_CSS_ROUTE}">',
            "</head>",
            "<body>",
            '  <div class="video-app">',
            '    <header class="hero-card">',
            '      <div class="hero-copy">',
            '        <p class="eyebrow">ZXTool HTTP Video</p>',
            f"        <h1>{safe_title}</h1>",
            f'        <p class="hero-meta">{safe_video_name}</p>',
            "      </div>",
            '      <div class="hero-actions">',
            '        <button id="startButton" class="primary-action" type="button" disabled>开始</button>',
            '        <button id="pauseButton" class="secondary-action" type="button" disabled>暂停</button>',
            '        <button id="screenshotButton" class="secondary-action" type="button" disabled>截屏</button>',
            "      </div>",
            "    </header>",
            '    <main class="content-grid">',
            '      <section class="player-card">',
            '        <div id="player" class="player-host"></div>',
            "      </section>",
            '      <aside class="side-card">',
            "        <h2>播放状态</h2>",
            '        <p id="statusText" class="status-text" data-tone="info">正在初始化播放器...</p>',
            '        <p class="hint-text">截屏会通过 Ajax 上传，并保存到视频所在目录。</p>',
            f'        <a class="video-link" href="{safe_video_url}">打开原始视频文件</a>',
            '        <p id="savedPathText" class="saved-path" hidden></p>',
            '        <div class="shot-preview">',
            "          <h3>最近一次截屏</h3>",
            '          <p id="shotEmpty" class="shot-empty">截屏后会在这里显示预览。</p>',
            '          <img id="shotPreview" alt="最近一次截屏预览" hidden>',
            "        </div>",
            "      </aside>",
            "    </main>",
            "  </div>",
            "  <script>",
            f"    window.__ZXTOOL_HTTP_VIDEO__ = {config_json};",
            "  </script>",
            f'  <script src="{HTTP_VIDEO_XGPLAYER_JS_ROUTE}"></script>',
            f'  <script src="{HTTP_VIDEO_PAGE_JS_ROUTE}"></script>',
            "</body>",
            "</html>",
        ]
    )


@lru_cache(maxsize=None)
def _read_bundled_asset(resource_path: tuple[str, ...]) -> bytes:
    """Read one bundled package asset as bytes."""
    resource = resources.files("zxtoolbox").joinpath(*resource_path)
    return resource.read_bytes()


def _serialize_script_json(data: dict[str, str]) -> str:
    """Serialize JSON safely for inline script usage."""
    text = json.dumps(data, ensure_ascii=False)
    return (
        text.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("</", "<\\/")
    )


def _parse_byte_range(range_header: str, file_size: int) -> tuple[int, int] | None:
    """Parse one HTTP Range header into an inclusive byte range."""
    if not range_header.startswith("bytes="):
        return None

    value = range_header[6:].strip()
    if "," in value or not value:
        return None

    start_text, _, end_text = value.partition("-")
    if not _:
        return None

    if start_text:
        try:
            start = int(start_text)
        except ValueError:
            return None

        if start < 0 or start >= file_size:
            return None

        if end_text:
            try:
                end = int(end_text)
            except ValueError:
                return None
            if end < start:
                return None
            end = min(end, file_size - 1)
            return start, end

        return start, file_size - 1

    if not end_text:
        return None

    try:
        suffix_length = int(end_text)
    except ValueError:
        return None

    if suffix_length <= 0:
        return None

    suffix_length = min(suffix_length, file_size)
    return file_size - suffix_length, file_size - 1


def _save_screenshot_data_url(
    screenshot_dir: Path,
    screenshot_base_name: str,
    data_url: str,
) -> Path:
    """Save one PNG data URL into the screenshot directory."""
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("only PNG data URLs are supported")

    encoded = data_url[len(prefix):]
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid PNG base64 payload") from exc

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{screenshot_base_name}-screenshot-{timestamp}.png"
    output_path = screenshot_dir / filename
    output_path.write_bytes(content)
    return output_path.resolve()
