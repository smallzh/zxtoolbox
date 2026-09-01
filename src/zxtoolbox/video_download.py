"""Online video download helpers built on top of yt-dlp."""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional

CLOUDFLARE_IMPERSONATION_HINT = (
    "Cloudflare anti-bot challenge detected. Retrying with browser impersonation."
)
IMPERSONATION_INSTALL_HINT = (
    "Browser impersonation requires the optional 'curl-cffi' dependency. "
    "Run 'uv sync' after updating dependencies, then try again."
)
IMPERSONATION_VERSION_HINT = (
    "Installed 'curl-cffi' is not compatible with this yt-dlp version. "
    "Use a supported version such as 'curl-cffi>=0.14,<0.15', then try again."
)
_BLOCK_FILLED = "#"
_BLOCK_EMPTY = "-"

# Supported audio output formats mapped to their ffmpeg codecs.
_AUDIO_CODEC_MAP = {
    "mp3": "libmp3lame",
    "aac": "aac",
    "m4a": "aac",
    "opus": "libopus",
    "wav": "pcm_s16le",
    "flac": "flac",
}
# Lossy formats that accept a bitrate flag.
_BITRATE_FORMATS = {"mp3", "aac", "m4a", "opus"}
# Public list of supported formats for CLI choices.
AUDIO_FORMATS = tuple(sorted(_AUDIO_CODEC_MAP))


def download_video(
    url: str,
    output_path: Optional[str] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> bool:
    """Download an online video with yt-dlp."""
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print("Error: yt-dlp not installed. Please run 'uv sync' to install dependencies.")
        return False

    ydl_opts = _build_ydl_opts(output_path, progress_callback)

    try:
        _download_once(YoutubeDL, url, _clone_ydl_opts(ydl_opts))
        print("-" * 60)
        print("Download completed successfully!")
        return True
    except Exception as exc:
        if _should_retry_with_impersonation(exc, ydl_opts):
            print(CLOUDFLARE_IMPERSONATION_HINT)
            try:
                _download_once(
                    YoutubeDL,
                    url,
                    _with_generic_impersonation(_clone_ydl_opts(ydl_opts)),
                )
                print("-" * 60)
                print("Download completed successfully!")
                return True
            except Exception as retry_exc:
                if _is_unsupported_impersonation_dependency(retry_exc):
                    print(IMPERSONATION_VERSION_HINT)
                if _is_missing_impersonation_dependency(retry_exc):
                    print(IMPERSONATION_INSTALL_HINT)
                print(f"\nError downloading video: {retry_exc}")
                return False

        if _is_unsupported_impersonation_dependency(exc):
            print(IMPERSONATION_VERSION_HINT)
        if _is_missing_impersonation_dependency(exc):
            print(IMPERSONATION_INSTALL_HINT)
        print(f"\nError downloading video: {exc}")
        return False


def _build_ydl_opts(
    output_path: Optional[str],
    progress_callback: Optional[Callable[[float], None]],
) -> dict[str, Any]:
    output_template, output_dir = _resolve_output(output_path)

    if output_dir and output_dir != Path("."):
        output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts: dict[str, Any] = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "progress_hooks": [_build_progress_hook(progress_callback)],
        "quiet": False,
        "no_warnings": False,
        "merge_output_format": "mp4",
    }

    if _check_ffmpeg():
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]
    else:
        print("Warning: ffmpeg not found. Video and audio may be downloaded separately.")
        print("To merge them automatically, please install ffmpeg.")

    return ydl_opts


def _resolve_output(output_path: Optional[str]) -> tuple[str, Path]:
    if not output_path:
        return "%(title)s.%(ext)s", Path(".")

    raw_path = Path(output_path)
    looks_like_directory = output_path.endswith(("/", "\\")) or raw_path.is_dir()
    if looks_like_directory:
        return str(raw_path / "%(title)s.%(ext)s"), raw_path

    return output_path, raw_path.parent if raw_path.parent != Path("") else Path(".")


def _build_progress_hook(
    progress_callback: Optional[Callable[[float], None]],
) -> Callable[[dict[str, Any]], None]:
    def progress_hook(download_status: dict[str, Any]) -> None:
        status = download_status.get("status")
        if status == "downloading":
            if not progress_callback:
                return
            downloaded_bytes = download_status.get("downloaded_bytes")
            total_bytes = download_status.get("total_bytes") or download_status.get("total_bytes_estimate")
            if downloaded_bytes and total_bytes:
                progress_callback((downloaded_bytes / total_bytes) * 100)
        elif status == "finished":
            if progress_callback:
                progress_callback(100.0)
            print(f"\nDownload finished: {download_status.get('filename', 'unknown')}")

    return progress_hook


def _download_once(youtube_dl_cls: Any, url: str, ydl_opts: dict[str, Any]) -> None:
    output_dir = _resolve_output_dir(ydl_opts.get("outtmpl"))
    print(f"Starting download from: {url}")
    print(f"Output path: {output_dir.resolve()}")
    print("-" * 60)

    with youtube_dl_cls(ydl_opts) as ydl:
        ydl.download([url])


def _clone_ydl_opts(ydl_opts: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(ydl_opts)


def _resolve_output_dir(outtmpl: Any) -> Path:
    if isinstance(outtmpl, dict):
        template = outtmpl.get("default") or next(
            (value for value in outtmpl.values() if isinstance(value, str)),
            "%(title)s.%(ext)s",
        )
    else:
        template = outtmpl or "%(title)s.%(ext)s"
    return Path(template).parent


def _with_generic_impersonation(ydl_opts: dict[str, Any]) -> dict[str, Any]:
    retry_opts = dict(ydl_opts)
    existing_extractor_args = dict(retry_opts.get("extractor_args", {}))
    generic_args = dict(existing_extractor_args.get("generic", {}))
    generic_args["impersonate"] = ["chrome"]
    existing_extractor_args["generic"] = generic_args
    retry_opts["extractor_args"] = existing_extractor_args
    return retry_opts


def _should_retry_with_impersonation(exc: Exception, ydl_opts: dict[str, Any]) -> bool:
    if _has_generic_impersonation(ydl_opts):
        return False

    message = str(exc).lower()
    return (
        "cloudflare anti-bot challenge" in message
        or "generic:impersonate" in message
        or ("http error 403" in message and "cloudflare" in message)
    )


def _has_generic_impersonation(ydl_opts: dict[str, Any]) -> bool:
    extractor_args = ydl_opts.get("extractor_args", {})
    generic_args = extractor_args.get("generic")
    if not isinstance(generic_args, dict):
        return False
    return bool(generic_args.get("impersonate"))


def _is_missing_impersonation_dependency(exc: Exception) -> bool:
    message = str(exc).lower()
    return "curl_cffi" in message or "curl-cffi" in message


def _is_unsupported_impersonation_dependency(exc: Exception) -> bool:
    message = str(exc).lower()
    return "only curl_cffi versions" in message or "curl_cffi versions" in message


def _check_ffmpeg() -> bool:
    """Return whether ffmpeg is available on PATH."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _print_progress_bar(progress: float, width: int = 50) -> None:
    """Print a simple progress bar."""
    filled = int(width * progress / 100)
    bar = _BLOCK_FILLED * filled + _BLOCK_EMPTY * (width - filled)
    percent = f"{progress:.1f}%"
    sys.stdout.write(f"\r|{bar}| {percent}")
    sys.stdout.flush()


def download_with_progress(url: str, output_path: Optional[str] = None) -> bool:
    """Download a video and render a CLI progress bar."""

    def progress_callback(progress: float) -> None:
        _print_progress_bar(progress)

    return download_video(url, output_path, progress_callback)


def extract_audio(
    input_file: str,
    output_path: Optional[str] = None,
    audio_format: str = "mp3",
    bitrate: str = "192k",
) -> bool:
    """Extract the audio track from a local video file into an audio file.

    Requires ffmpeg on PATH. The audio stream is re-encoded with the
    requested codec; lossy formats accept a bitrate (default 192k).
    """
    source = Path(input_file)
    if not source.is_file():
        print(f"Error: input file not found: {input_file}")
        return False

    audio_format = audio_format.lower().lstrip(".")
    codec = _AUDIO_CODEC_MAP.get(audio_format)
    if codec is None:
        supported = ", ".join(AUDIO_FORMATS)
        print(f"Error: unsupported audio format '{audio_format}'. Supported: {supported}")
        return False

    if not _check_ffmpeg():
        print("Error: ffmpeg not found. Audio extraction requires ffmpeg on PATH.")
        return False

    output = _resolve_audio_output(source, output_path, audio_format)
    output.parent.mkdir(parents=True, exist_ok=True)

    command = ["ffmpeg", "-y", "-i", str(source), "-vn", "-acodec", codec]
    if audio_format in _BITRATE_FORMATS:
        command += ["-b:a", bitrate]
    command.append(str(output))

    print(f"Extracting audio from: {source}")
    print(f"Output path: {output.resolve()}")
    print("-" * 60)

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        print("Error: ffmpeg not found. Audio extraction requires ffmpeg on PATH.")
        return False

    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip().splitlines()[-5:]
        print("Error: ffmpeg failed to extract audio:")
        for line in stderr_tail:
            print(f"  {line}")
        return False

    print("-" * 60)
    print(f"Audio extracted successfully: {output}")
    return True


def _resolve_audio_output(
    source: Path,
    output_path: Optional[str],
    audio_format: str,
) -> Path:
    """Resolve the audio output path.

    - No output: same directory as the source, same stem, target extension.
    - Output is a directory (or ends with a separator): directory + source stem.
    - Output is a file path: keep it but force the target extension.
    """
    default_name = f"{source.stem}.{audio_format}"
    if not output_path:
        return source.parent / default_name

    out = Path(output_path)
    if output_path.endswith(("/", "\\")) or out.is_dir():
        return out / default_name
    return out.with_suffix(f".{audio_format}")


if __name__ == "__main__":
    test_url = input("Enter video URL: ").strip()
    if test_url:
        download_with_progress(test_url)
    else:
        print("No URL provided.")
