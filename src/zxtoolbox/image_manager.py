"""Image compression and resizing utilities.

Provides resize (dimension change), compress (file-size reduction) and batch
WebP conversion for common image formats (JPEG, PNG, WebP). Uses Pillow (PIL)
as the backend.

Examples:
    >>> from zxtoolbox.image_manager import resize_image, compress_image, batch_compress_webp
    >>> resize_image("photo.jpg", "photo_thumb.jpg", width=128)
    >>> compress_image("photo.png", "photo_opt.jpg", max_size=200_000, output_format="jpeg")
    >>> batch_compress_webp("./images", max_size=20_480, keep_original=True)
"""

from __future__ import annotations

import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

# ── Format helpers ──────────────────────────────────────────────────────────

_EXTENSION_MAP: dict[str, str] = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WebP",
}

_SUPPORTED_EXTENSIONS = frozenset(_EXTENSION_MAP.keys())

# PIL format names for save()
_SAVE_FORMAT_MAP: dict[str, str] = {
    "jpeg": "JPEG",
    "jpg": "JPEG",
    "png": "PNG",
    "webp": "WebP",
}


def _detect_format(path: Path) -> str:
    """Detect the image format from a file path's extension.

    Args:
        path: File path.

    Returns:
        PIL format string (e.g. ``"JPEG"``).

    Raises:
        ValueError: If the extension is not supported.
    """
    ext = path.suffix.lower()
    fmt = _EXTENSION_MAP.get(ext)
    if fmt is None:
        raise ValueError(
            f"Unsupported image format: {ext}. "
            f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )
    return fmt


def _normalise_format(format_name: str) -> str:
    """Normalise a user-supplied format name to PIL's internal name.

    Args:
        format_name: ``"jpeg"``, ``"jpg"``, ``"png"``, or ``"webp"``.

    Returns:
        ``"JPEG"``, ``"PNG"``, or ``"WebP"``.

    Raises:
        ValueError: On unknown format.
    """
    key = format_name.strip().lower()
    fmt = _SAVE_FORMAT_MAP.get(key)
    if fmt is None:
        raise ValueError(
            f"Unsupported output format: {format_name!r}. "
            f"Supported: {', '.join(sorted(_SAVE_FORMAT_MAP))}"
        )
    return fmt


def _make_output_path(
    input_path: Path,
    *,
    suffix: str,
    output_format: str | None = None,
) -> Path:
    """Build an output path from an input path.

    If *output_format* is given the extension is changed to match that
    format; otherwise the original extension is kept and *suffix* is
    inserted before it.
    """
    if output_format:
        ext_map = {"JPEG": ".jpg", "PNG": ".png", "WebP": ".webp"}
        return input_path.with_suffix(ext_map[output_format])
    # Insert suffix before original extension
    return input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")


# ── Size parsing ────────────────────────────────────────────────────────────

_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(K|M|KB|MB)?$", re.IGNORECASE)


def parse_size(text: str) -> int:
    """Parse a human-readable size string into bytes.

    Accepts suffixes ``K`` / ``KB`` (kibibytes) and ``M`` / ``MB`` (mebibytes).
    Plain numbers are treated as bytes.

    Args:
        text: e.g. ``"200K"``, ``"1.5M"``, ``"512000"``.

    Returns:
        Size in bytes.

    Raises:
        ValueError: If *text* cannot be parsed.
    """
    match = _SIZE_RE.match(text.strip())
    if not match:
        raise ValueError(
            f"Cannot parse size: {text!r}. "
            f"Expected a number optionally followed by K/KB/M/MB "
            f"(e.g. 200K, 1.5M, 512000)."
        )

    value = float(match.group(1))
    unit = (match.group(2) or "").upper()

    multipliers = {"K": 1024, "KB": 1024, "M": 1024 ** 2, "MB": 1024 ** 2}
    multiplier = multipliers.get(unit, 1)
    return int(value * multiplier)


# ── Resize ──────────────────────────────────────────────────────────────────


def resize_image(
    input_path: str | Path,
    output_path: str | Path,
    width: int | None = None,
    height: int | None = None,
) -> Path:
    """Resize an image to the given dimensions while keeping content intact.

    At least one of *width* or *height* must be provided.  If only one is
    given the other is automatically scaled to preserve the original aspect
    ratio.  When both are supplied the image is resized to exactly those
    dimensions (content is preserved but the aspect ratio *may* change).

    Args:
        input_path: Path to the source image.
        output_path: Where to write the resized image.
        width: Target width in pixels.
        height: Target height in pixels.

    Returns:
        The resolved ``output_path``.

    Raises:
        FileNotFoundError: If *input_path* does not exist.
        ValueError: If neither *width* nor *height* is given, or if the
            image format is unsupported.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    if width is None and height is None:
        raise ValueError("At least one of --width or --height is required.")

    img = Image.open(input_path)
    orig_w, orig_h = img.size

    if width is not None and height is not None:
        new_size = (width, height)
    elif width is not None:
        ratio = width / orig_w
        new_size = (width, max(1, int(orig_h * ratio)))
    else:  # height is not None
        ratio = height / orig_h
        new_size = (max(1, int(orig_w * ratio)), height)

    resized = img.resize(new_size, Image.LANCZOS)

    # Preserve colour mode for formats that don't support alpha
    fmt = _detect_format(output_path)
    if fmt == "JPEG" and resized.mode in ("RGBA", "P"):
        resized = resized.convert("RGB")

    resized.save(output_path, format=fmt)
    print(f"[OK] Resized image saved to: {output_path}")
    print(f"  {orig_w}x{orig_h}  ->  {new_size[0]}x{new_size[1]}")
    return output_path.resolve()


# ── Compress ────────────────────────────────────────────────────────────────


def _binary_search_quality(
    img: Image.Image,
    output_path: Path,
    target_bytes: int,
    save_format: str,
    min_q: int = 5,
    max_q: int = 95,
) -> int:
    """Binary-search for the highest JPEG/WebP quality that stays under
    *target_bytes*.

    Args:
        img: The PIL ``Image`` to encode.
        output_path: Temporary path to write to (will be overwritten).
        target_bytes: Maximum allowed file size.
        save_format: ``"JPEG"`` or ``"WebP"``.
        min_q: Lower quality bound.
        max_q: Upper quality bound.

    Returns:
        The best quality value found (``min_q`` if even the lowest quality
        exceeds the target).
    """
    save_kwargs: dict[str, Any] = {"format": save_format, "optimize": True}
    if save_format in ("JPEG", "WebP"):
        save_kwargs["quality"] = 85  # placeholder

    # If even the lowest quality is too large, return min_q
    save_kwargs["quality"] = min_q
    img.save(output_path, **save_kwargs)
    if output_path.stat().st_size > target_bytes:
        return min_q

    while max_q - min_q > 1:
        mid = (min_q + max_q) // 2
        save_kwargs["quality"] = mid
        img.save(output_path, **save_kwargs)
        if output_path.stat().st_size > target_bytes:
            max_q = mid
        else:
            min_q = mid

    return min_q


def compress_image(
    input_path: str | Path,
    output_path: str | Path,
    max_size: int | None = None,
    quality: int | None = None,
    output_format: str | None = None,
) -> Path:
    """Compress an image, optionally targeting a maximum file size.

    * JPEG / WebP *: When *max_size* is given without *quality*, binary-search
      for the best quality that fits under the limit.
    * PNG          : Uses ``optimize=True``.  Binary search is not effective
      on PNG; if the target size is not met a warning is printed.

    Args:
        input_path: Source image path.
        output_path: Destination path.
        max_size: Target maximum file size in bytes.
        quality: Output quality 1-100 (overrides binary search when set).
        output_format: ``"jpeg"`` / ``"png"`` / ``"webp"`` (default: same as input).

    Returns:
        The resolved ``output_path``.

    Raises:
        FileNotFoundError: If *input_path* does not exist.
        ValueError: On unsupported formats or invalid parameters.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    img = Image.open(input_path)

    # Determine output format
    if output_format:
        save_format = _normalise_format(output_format)
    else:
        save_format = _detect_format(input_path)

    # Handle alpha channel for JPEG output
    if save_format == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    save_kwargs: dict[str, Any] = {
        "format": save_format,
        "optimize": True,
    }

    if save_format in ("JPEG", "WebP"):
        if quality is not None:
            # Fixed quality — no size guarantee
            save_kwargs["quality"] = quality
            img.save(output_path, **save_kwargs)
        elif max_size is not None:
            # Binary search for optimal quality
            best_q = _binary_search_quality(
                img, output_path, max_size, save_format
            )
            save_kwargs["quality"] = best_q
            img.save(output_path, **save_kwargs)
            actual_size = output_path.stat().st_size
            print(
                f"[INFO] Quality {best_q} selected "
                f"(target ≤ {max_size} B, actual {actual_size} B)"
            )
        else:
            # Neither quality nor max_size – just save with defaults
            img.save(output_path, **save_kwargs)
    else:
        # PNG — no quality parameter
        img.save(output_path, **save_kwargs)
        if max_size is not None:
            actual = output_path.stat().st_size
            if actual > max_size:
                print(
                    f"[WARN] PNG output size ({actual} B) exceeds target "
                    f"({max_size} B). Consider converting to JPEG/WebP "
                    f"with --format jpeg or --format webp."
                )

    actual_size = output_path.stat().st_size
    input_size = input_path.stat().st_size
    ratio = (1 - actual_size / input_size) * 100 if input_size else 0

    print(f"[OK] Compressed image saved to: {output_path}")
    print(f"  Size: {_human_size(input_size)}  ->  {_human_size(actual_size)}")
    print(f"  Reduction: {ratio:.1f}%")
    return output_path.resolve()


def _human_size(size_bytes: int) -> str:
    """Format a byte count into a human-readable string."""
    if size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


# ── Batch webp compression ──────────────────────────────────────────────────

DEFAULT_MAX_SIZE_BYTES = 20 * 1024  # 20K default target


def _unique_backup_path(backup_dir: Path, filename: str) -> Path:
    """Return a non-conflicting path inside *backup_dir* for *filename*."""
    candidate = backup_dir / filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while candidate.exists():
        candidate = backup_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def batch_compress_webp(
    directory: str | Path,
    max_size: int = DEFAULT_MAX_SIZE_BYTES,
    keep_original: bool = False,
    backup_dir: str | Path | None = None,
) -> dict[str, int]:
    """Batch-compress every supported image in *directory* into WebP.

    Processes the top-level files of *directory* only (no recursion).
    Each supported image (JPEG / PNG / WebP) is re-encoded as WebP with the
    same file stem.  A single quality search pass is performed (best effort);
    images that still exceed *max_size* are kept and reported.

    Behavior:
      * Files already at or below *max_size* are left untouched.
      * ``keep_original=False``: the source file is deleted after a successful
        conversion.
      * ``keep_original=True``: the source file is moved first into
        *backup_dir* (default: ``<directory>/originals``).

    Args:
        directory: Folder containing the images.
        max_size: Target maximum file size in bytes (default 20 KiB).
        keep_original: Whether to preserve the original files.
        backup_dir: Where originals go when *keep_original* is True.

    Returns:
        A summary dict ``{"converted": n, "skipped": n, "failed": n}``.

    Raises:
        FileNotFoundError: If *directory* does not exist.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Input directory not found: {directory}")

    if backup_dir is None:
        backup_dir = directory / "originals"
    else:
        backup_dir = Path(backup_dir)

    images = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in _EXTENSION_MAP
    )

    summary = {"converted": 0, "skipped": 0, "failed": 0}
    if not images:
        print(f"No supported images found in: {directory}")
        return summary

    print(f"Batch compressing {len(images)} image(s) in: {directory}")
    print(f"Target max size: {_human_size(max_size)}")
    if keep_original:
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"Originals will be kept in: {backup_dir}")
    else:
        print("Original files will be deleted after conversion")
    print("-" * 60)

    for path in images:
        if path.stat().st_size <= max_size:
            print(f"[SKIP] {path.name}: already {_human_size(path.stat().st_size)} (<= {_human_size(max_size)})")
            summary["skipped"] += 1
            continue

        source = path
        if keep_original:
            backup_target = _unique_backup_path(backup_dir, path.name)
            try:
                shutil.move(str(path), str(backup_target))
            except OSError as exc:
                print(f"[ERROR] Cannot move original {path.name}: {exc}")
                summary["failed"] += 1
                continue
            source = backup_target

        output = directory / f"{path.stem}.webp"
        was_in_place = source.resolve() == output.resolve()
        try:
            if was_in_place:
                # Re-encoding a WebP in place: write to a temp file first.
                fd, temp_name = tempfile.mkstemp(suffix=".webp", dir=directory)
                os.close(fd)
                try:
                    compress_image(
                        input_path=source,
                        output_path=temp_name,
                        max_size=max_size,
                        output_format="webp",
                    )
                    os.replace(temp_name, output)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
            else:
                compress_image(
                    input_path=source,
                    output_path=output,
                    max_size=max_size,
                    output_format="webp",
                )
        except (OSError, ValueError) as exc:
            print(f"[ERROR] Failed to compress {path.name}: {exc}")
            if keep_original:
                try:
                    shutil.move(str(backup_target), str(path))
                except OSError:
                    pass
            summary["failed"] += 1
            continue

        if output.stat().st_size > max_size:
            print(
                f"[WARN] {output.name} still exceeds {_human_size(max_size)} "
                f"(actual {_human_size(output.stat().st_size)}); kept best-effort result"
            )

        if not keep_original and not was_in_place:
            try:
                path.unlink()
            except OSError as exc:
                print(f"[WARN] Cannot delete original {path.name}: {exc}")

        summary["converted"] += 1

    print("-" * 60)
    print(
        f"Done: {summary['converted']} converted, "
        f"{summary['skipped']} skipped, {summary['failed']} failed"
    )
    return summary


if __name__ == "__main__":
    # Simple CLI entry for quick testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m zxtoolbox.image_manager <command> [args]")
        print("Commands: resize, compress")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "resize":
        resize_image(
            sys.argv[2],
            sys.argv[3],
            width=int(sys.argv[4]) if len(sys.argv) > 4 else None,
            height=int(sys.argv[5]) if len(sys.argv) > 5 else None,
        )
    elif cmd == "compress":
        compress_image(
            sys.argv[2],
            sys.argv[3],
            max_size=int(sys.argv[4]) if len(sys.argv) > 4 else None,
            quality=int(sys.argv[5]) if len(sys.argv) > 5 else None,
            output_format=sys.argv[6] if len(sys.argv) > 6 else None,
        )
    else:
        print(f"Unknown command: {cmd}")
