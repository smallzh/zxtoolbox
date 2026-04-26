"""静态文件 HTTP 服务模块。"""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve_directory(
    directory: str | Path = ".",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """启动静态文件 HTTP 服务。

    Args:
        directory: 要公开的静态文件目录，默认当前目录。
        host: 监听地址，默认 127.0.0.1。
        port: 监听端口，默认 8000。
    """
    directory_path = Path(directory).resolve()

    if not directory_path.exists():
        print(f"[ERROR] 目录不存在: {directory_path}")
        return

    if not directory_path.is_dir():
        print(f"[ERROR] 目标不是目录: {directory_path}")
        return

    handler_class = partial(
        SimpleHTTPRequestHandler,
        directory=str(directory_path),
    )

    try:
        httpd = ThreadingHTTPServer((host, port), handler_class)
    except OSError as e:
        print(f"[ERROR] HTTP 服务启动失败: {e}")
        return

    try:
        bound_host, bound_port = httpd.server_address[:2]
        display_host = host or bound_host

        print(f"静态目录: {directory_path}")
        print(f"服务地址: http://{display_host}:{bound_port}")
        print("按 Ctrl+C 停止服务")

        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] HTTP 服务已停止")
    finally:
        httpd.server_close()
