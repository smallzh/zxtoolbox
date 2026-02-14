"""
在线视频下载模块

基于 yt-dlp 库实现网页视频下载功能，支持进度显示。
"""

import os
import sys
from typing import Optional, Callable


def download_video(
    url: str,
    output_path: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None
) -> bool:
    """
    下载在线视频

    Args:
        url: 视频URL地址
        output_path: 输出文件路径或目录，默认为当前目录
        progress_callback: 进度回调函数，接收0-100的进度值

    Returns:
        bool: 下载是否成功
    """
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print("Error: yt-dlp not installed. Please run 'uv sync' to install dependencies.")
        return False

    # 处理输出路径
    if output_path:
        output_dir = os.path.dirname(output_path) if os.path.dirname(output_path) else "."
        output_template = output_path
    else:
        output_dir = "."
        output_template = "%(title)s.%(ext)s"

    # 确保输出目录存在
    if output_dir and output_dir != ".":
        os.makedirs(output_dir, exist_ok=True)

    # 进度钩子
    def progress_hook(d):
        if d['status'] == 'downloading':
            if progress_callback and 'downloaded_bytes' in d and 'total_bytes' in d:
                if d['total_bytes'] > 0:
                    progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    progress_callback(progress)
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback(100.0)
            print(f"\nDownload finished: {d.get('filename', 'unknown')}")

    # yt-dlp 配置选项
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'progress_hooks': [progress_hook],
        'quiet': False,
        'no_warnings': False,
        'merge_output_format': 'mp4',
    }

    # 如果有ffmpeg，启用合并功能
    if _check_ffmpeg():
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
    else:
        print("Warning: ffmpeg not found. Video and audio may be downloaded separately.")
        print("To merge them automatically, please install ffmpeg.")

    try:
        print(f"Starting download from: {url}")
        print(f"Output path: {os.path.abspath(output_dir)}")
        print("-" * 60)

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print("-" * 60)
        print("Download completed successfully!")
        return True

    except Exception as e:
        print(f"\nError downloading video: {e}")
        return False


def _check_ffmpeg() -> bool:
    """检查系统是否安装了 ffmpeg"""
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _print_progress_bar(progress: float, width: int = 50):
    """打印进度条"""
    filled = int(width * progress / 100)
    bar = '█' * filled + '░' * (width - filled)
    percent = f"{progress:.1f}%"
    sys.stdout.write(f"\r|{bar}| {percent}")
    sys.stdout.flush()


def download_with_progress(url: str, output_path: Optional[str] = None) -> bool:
    """
    下载视频并显示进度条

    Args:
        url: 视频URL地址
        output_path: 输出文件路径或目录

    Returns:
        bool: 下载是否成功
    """
    def progress_callback(progress: float):
        _print_progress_bar(progress)

    return download_video(url, output_path, progress_callback)


if __name__ == "__main__":
    # 测试代码
    test_url = input("Enter video URL: ").strip()
    if test_url:
        download_with_progress(test_url)
    else:
        print("No URL provided.")
