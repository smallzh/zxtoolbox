"""Tests for zxtoolbox.image_manager module."""

import io
import random
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from zxtoolbox.image_manager import (
    _detect_format,
    _normalise_format,
    _human_size,
    parse_size,
    resize_image,
    compress_image,
    batch_compress_webp,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def rgb_image(tmp_path: Path) -> Path:
    """Create a 200×200 RGB JPEG test image."""
    path = tmp_path / "test.jpg"
    img = Image.new("RGB", (200, 200), color="red")
    img.save(path, format="JPEG", quality=95)
    return path


@pytest.fixture
def rgba_image(tmp_path: Path) -> Path:
    """Create a 100×100 RGBA PNG test image."""
    path = tmp_path / "test.png"
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    img.save(path, format="PNG")
    return path


@pytest.fixture
def webp_image(tmp_path: Path) -> Path:
    """Create a 50×50 WebP test image."""
    path = tmp_path / "test.webp"
    img = Image.new("RGB", (50, 50), color="blue")
    img.save(path, format="WebP", quality=90)
    return path


# ── Test helpers ─────────────────────────────────────────────────────────────


class TestHelpers:
    def test_detect_format_jpg(self, rgb_image: Path):
        assert _detect_format(rgb_image) == "JPEG"

    def test_detect_format_jpeg(self, tmp_path: Path):
        p = tmp_path / "x.jpeg"
        p.write_text("dummy")
        assert _detect_format(p) == "JPEG"

    def test_detect_format_png(self, rgba_image: Path):
        assert _detect_format(rgba_image) == "PNG"

    def test_detect_format_webp(self, webp_image: Path):
        assert _detect_format(webp_image) == "WebP"

    def test_detect_format_unsupported(self, tmp_path: Path):
        p = tmp_path / "x.bmp"
        with pytest.raises(ValueError, match="Unsupported"):
            _detect_format(p)

    def test_normalise_format(self):
        assert _normalise_format("jpeg") == "JPEG"
        assert _normalise_format("jpg") == "JPEG"
        assert _normalise_format("png") == "PNG"
        assert _normalise_format("webp") == "WebP"

    def test_normalise_format_invalid(self):
        with pytest.raises(ValueError, match="Unsupported"):
            _normalise_format("gif")

    def test_human_size_bytes(self):
        assert _human_size(500) == "500 B"

    def test_human_size_kb(self):
        assert _human_size(2048) == "2.0 KB"

    def test_human_size_mb(self):
        assert _human_size(3_145_728) == "3.0 MB"

    def test_parse_size_bytes(self):
        assert parse_size("512") == 512

    def test_parse_size_kb(self):
        assert parse_size("200K") == 204800
        assert parse_size("1.5KB") == 1536

    def test_parse_size_mb(self):
        assert parse_size("2M") == 2_097_152
        assert parse_size("1MB") == 1_048_576

    def test_parse_size_invalid(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_size("abc")


# ── Test resize ──────────────────────────────────────────────────────────────


class TestResize:
    def test_resize_both_dimensions(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        result = resize_image(rgb_image, out, width=100, height=100)
        assert result == out.resolve()
        with Image.open(out) as img:
            assert img.size == (100, 100)

    def test_resize_only_width(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        resize_image(rgb_image, out, width=50)
        with Image.open(out) as img:
            assert img.width == 50
            assert img.height == 50  # aspect ratio preserved (200×200)

    def test_resize_only_height(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        resize_image(rgb_image, out, height=80)
        with Image.open(out) as img:
            assert img.height == 80
            assert img.width == 80  # aspect ratio preserved

    def test_resize_missing_dimensions(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        with pytest.raises(ValueError, match="At least one"):
            resize_image(rgb_image, out)

    def test_resize_file_not_found(self, tmp_path: Path):
        out = tmp_path / "out.jpg"
        with pytest.raises(FileNotFoundError, match="not found"):
            resize_image(tmp_path / "nonexistent.png", out, width=100)

    def test_resize_converts_rgba_to_rgb_for_jpeg(self, rgba_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        resize_image(rgba_image, out, width=50)
        with Image.open(out) as img:
            assert img.mode == "RGB"
            assert img.size == (50, 50)

    def test_resize_png_to_png(self, rgba_image: Path, tmp_path: Path):
        out = tmp_path / "out.png"
        resize_image(rgba_image, out, width=75)
        with Image.open(out) as img:
            assert img.mode == "RGBA"
            assert img.size == (75, 75)

    def test_resize_webp(self, webp_image: Path, tmp_path: Path):
        out = tmp_path / "out.webp"
        resize_image(webp_image, out, width=25)
        with Image.open(out) as img:
            assert img.size == (25, 25)


# ── Test compress ────────────────────────────────────────────────────────────


class TestCompress:
    def test_compress_jpeg_default(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        result = compress_image(rgb_image, out)
        assert result == out.resolve()
        assert out.stat().st_size > 0

    def test_compress_jpeg_with_quality(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        compress_image(rgb_image, out, quality=10)
        with Image.open(out) as img:
            assert img.size == (200, 200)

    def test_compress_jpeg_to_target_size(self, rgb_image: Path, tmp_path: Path):
        out = tmp_path / "out.jpg"
        target = 10000  # 10 KB
        compress_image(rgb_image, out, max_size=target)
        # Binary search should get close to the target
        actual = out.stat().st_size
        # Allow some tolerance — binary search may not hit exactly
        assert actual <= target * 1.15, f"Expected ≤{target}, got {actual}"

    def test_compress_png(self, rgba_image: Path, tmp_path: Path):
        out = tmp_path / "out.png"
        compress_image(rgba_image, out)
        with Image.open(out) as img:
            assert img.mode == "RGBA"

    def test_compress_png_with_format_conversion(self, rgba_image: Path, tmp_path: Path):
        """PNG → JPEG conversion should drop alpha."""
        out = tmp_path / "out.jpg"
        compress_image(rgba_image, out, output_format="jpeg")
        with Image.open(out) as img:
            assert img.mode == "RGB"

    def test_compress_webp(self, webp_image: Path, tmp_path: Path):
        out = tmp_path / "out.webp"
        compress_image(webp_image, out, quality=50)
        with Image.open(out) as img:
            assert img.size == (50, 50)

    def test_compress_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            compress_image(tmp_path / "nonexistent.jpg", tmp_path / "out.jpg")

    def test_compress_no_params(self, rgb_image: Path, tmp_path: Path):
        """Calling compress with no size/quality should still produce output."""
        out = tmp_path / "out.jpg"
        compress_image(rgb_image, out)
        assert out.exists()


# ── Test batch webp compression ──────────────────────────────────────────────


class TestBatchCompressWebp:
    """Test batch WebP compression."""

    @staticmethod
    def _make_noisy(path: Path, size: int = 400, quality: int = 95) -> Path:
        """Create a noisy image guaranteed to be much larger than a few KB."""
        rnd = random.Random(42)
        img = Image.new("RGB", (size, size))
        pixels = [
            (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
            for _ in range(size * size)
        ]
        img.putdata(pixels)
        img.save(path, format="PNG" if path.suffix == ".png" else "JPEG", quality=quality)
        return path

    @staticmethod
    def _make_tiny_png(path: Path) -> Path:
        img = Image.new("RGB", (4, 4), color="blue")
        img.save(path, format="PNG")
        return path

    def test_batch_deletes_original_and_writes_webp(self, tmp_path: Path):
        photo = self._make_noisy(tmp_path / "photo.jpg")
        threshold = photo.stat().st_size // 2

        summary = batch_compress_webp(tmp_path, max_size=threshold)

        assert summary == {"converted": 1, "skipped": 0, "failed": 0}
        out = tmp_path / "photo.webp"
        assert out.exists()
        assert not photo.exists()
        with Image.open(out) as img:
            assert img.format == "WEBP"
            assert img.size == (400, 400)

    def test_batch_keep_original_moves_to_backup_dir(self, tmp_path: Path):
        photo = self._make_noisy(tmp_path / "photo.jpg")
        threshold = photo.stat().st_size // 2

        summary = batch_compress_webp(tmp_path, max_size=threshold, keep_original=True)

        assert summary["converted"] == 1
        originals = tmp_path / "originals"
        assert originals.is_dir()
        assert (originals / "photo.jpg").exists()
        assert (tmp_path / "photo.webp").exists()
        assert not photo.exists()

    def test_batch_keep_original_custom_backup_dir(self, tmp_path: Path):
        photo = self._make_noisy(tmp_path / "photo.jpg")
        threshold = photo.stat().st_size // 2
        bak = tmp_path / "my_backup"

        batch_compress_webp(
            tmp_path, max_size=threshold, keep_original=True, backup_dir=bak
        )

        assert (bak / "photo.jpg").exists()
        assert (tmp_path / "photo.webp").exists()

    def test_batch_keep_original_avoids_name_conflicts(self, tmp_path: Path):
        """Second run with the same filename must not overwrite a backup."""
        photo = self._make_noisy(tmp_path / "photo.jpg")
        threshold = photo.stat().st_size // 2
        batch_compress_webp(tmp_path, max_size=threshold, keep_original=True)
        assert (tmp_path / "originals" / "photo.jpg").exists()

        # Simulate a second batch with a fresh image of the same name.
        photo2 = self._make_noisy(tmp_path / "photo.jpg")
        threshold2 = photo2.stat().st_size // 2
        batch_compress_webp(tmp_path, max_size=threshold2, keep_original=True)
        originals = tmp_path / "originals"
        assert (originals / "photo_1.jpg").exists()

    def test_batch_skips_small_images(self, tmp_path: Path):
        noise = self._make_noisy(tmp_path / "big.jpg")
        tiny = self._make_tiny_png(tmp_path / "small.png")
        threshold = tiny.stat().st_size + 10  # only the tiny file is under threshold

        summary = batch_compress_webp(tmp_path, max_size=threshold)

        assert summary == {"converted": 1, "skipped": 1, "failed": 0}
        assert tiny.exists()  # untouched
        assert not (tmp_path / "small.webp").exists()
        assert (tmp_path / "big.webp").exists()
        assert not noise.exists()

    def test_batch_skips_files_below_threshold_even_with_keep_original(
        self, tmp_path: Path
    ):
        self._make_tiny_png(tmp_path / "small.png")
        summary = batch_compress_webp(
            tmp_path, max_size=1024 * 1024, keep_original=True
        )
        assert summary == {"converted": 0, "skipped": 1, "failed": 0}
        assert (tmp_path / "small.png").exists()

    def test_batch_webp_input_in_place(self, tmp_path: Path):
        """Re-encoding a WebP in place must keep the file and not delete it."""
        clip = tmp_path / "clip.webp"
        rnd = random.Random(7)
        img = Image.new("RGB", (300, 300))
        img.putdata(
            [
                (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
                for _ in range(300 * 300)
            ]
        )
        img.save(clip, format="WebP", quality=95)
        threshold = clip.stat().st_size // 2

        summary = batch_compress_webp(tmp_path, max_size=threshold)

        assert summary == {"converted": 1, "skipped": 0, "failed": 0}
        assert clip.exists()
        with Image.open(clip) as opened:
            assert opened.format == "WEBP"

    def test_batch_warns_when_still_over_threshold(self, tmp_path: Path, capsys):
        photo = self._make_noisy(tmp_path / "photo.jpg")

        summary = batch_compress_webp(tmp_path, max_size=1)

        assert summary["converted"] == 1
        captured = capsys.readouterr().out
        assert "still exceeds" in captured

    def test_batch_ignores_non_image_files(self, tmp_path: Path):
        (tmp_path / "readme.txt").write_text("hello")
        summary = batch_compress_webp(tmp_path, max_size=1)
        assert summary == {"converted": 0, "skipped": 0, "failed": 0}

    def test_batch_empty_directory(self, tmp_path: Path, capsys):
        summary = batch_compress_webp(tmp_path, max_size=1)
        assert summary == {"converted": 0, "skipped": 0, "failed": 0}
        assert "No supported images found" in capsys.readouterr().out

    def test_batch_directory_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            batch_compress_webp(tmp_path / "missing", max_size=1)
