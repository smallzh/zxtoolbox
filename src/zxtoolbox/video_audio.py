"""Audio extraction from local video files using ffmpeg.

Online video download functionality has been migrated to the standalone
``zxtoolx`` project (d:/zyj/files/zxworkstation_space/scripts/zxtoolx).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

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
        # ffmpeg writes UTF-8 output; on Chinese Windows text=True would decode
        # with GBK and crash on non-GBK bytes (UnicodeDecodeError in the
        # reader thread). Decode as UTF-8 and replace undecodable bytes.
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
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


def _check_ffmpeg() -> bool:
    """Return whether ffmpeg is available on PATH."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
