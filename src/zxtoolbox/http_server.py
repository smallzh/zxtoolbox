"""Static file HTTP server helpers."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve_directory(
    directory: str | Path = ".",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Start a static file HTTP server for one directory."""
    directory_path = Path(directory).resolve()

    if not directory_path.exists():
        print(f"[ERROR] directory does not exist: {directory_path}")
        return

    if not directory_path.is_dir():
        print(f"[ERROR] target is not a directory: {directory_path}")
        return

    handler_class = partial(
        SimpleHTTPRequestHandler,
        directory=str(directory_path),
    )

    try:
        httpd = ThreadingHTTPServer((host, port), handler_class)
    except OSError as exc:
        print(f"[ERROR] failed to start HTTP server: {exc}")
        return

    try:
        bound_host, bound_port = httpd.server_address[:2]
        display_host = host or bound_host

        print(f"Serving directory: {directory_path}")
        print(f"Server address: http://{display_host}:{bound_port}")
        print("Press Ctrl+C to stop the server")

        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] HTTP server stopped")
    finally:
        httpd.server_close()
