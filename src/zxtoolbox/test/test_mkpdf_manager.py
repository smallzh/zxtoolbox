"""Tests for zxtoolbox.mkpdf_manager."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import shutil
import zipfile

import pytest

from zxtoolbox import mkpdf_manager as mpdf


@pytest.fixture
def tmp_path():
    root = Path("dist/test_tmp_mkpdf").resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    yield root
    if root.exists():
        shutil.rmtree(root)


def test_collect_single_markdown_source_uses_heading_as_title(tmp_path):
    markdown_file = tmp_path / "demo.md"
    markdown_file.write_text("# Hello World\n\ncontent", encoding="utf-8")

    sources, title = mpdf._collect_markdown_sources(markdown_file)

    assert title == "Hello World"
    assert len(sources) == 1
    assert sources[0].relative_path.as_posix() == "demo.md"


def test_collect_directory_uses_readme_by_default(tmp_path):
    (tmp_path / "README.md").write_text("# Root Readme\n", encoding="utf-8")
    (tmp_path / "index.md").write_text("# Index\n", encoding="utf-8")

    sources, title = mpdf._collect_markdown_sources(tmp_path)

    assert title == "Root Readme"
    assert len(sources) == 1
    assert sources[0].relative_path.as_posix() == "README.md"


def test_collect_directory_uses_custom_entry_file(tmp_path):
    (tmp_path / "README.md").write_text("# Root Readme\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")

    sources, title = mpdf._collect_markdown_sources(
        tmp_path,
        directory_file="docs/guide.md",
    )

    assert title == "Guide"
    assert len(sources) == 1
    assert sources[0].relative_path.as_posix() == "docs/guide.md"


def test_collect_directory_rejects_entry_file_outside_directory(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")

    with pytest.raises(ValueError, match="within the input directory"):
        mpdf._collect_markdown_sources(tmp_path, directory_file=outside)


def test_render_markdown_html_rewrites_local_image_to_file_uri(tmp_path):
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"PNGDATA")
    markdown_file = tmp_path / "demo.md"
    markdown_file.write_text("# Demo\n\n![alt](image.png)", encoding="utf-8")
    source = mpdf._load_markdown_source(markdown_file, tmp_path)

    html = mpdf._render_markdown_html(source, enable_mermaid=False)

    assert image_path.resolve().as_uri() in html


def test_render_markdown_html_preserves_http_links(tmp_path):
    markdown_file = tmp_path / "demo.md"
    markdown_file.write_text("[site](https://example.com)", encoding="utf-8")
    source = mpdf._load_markdown_source(markdown_file, tmp_path)

    html = mpdf._render_markdown_html(source, enable_mermaid=False)

    assert 'href="https://example.com"' in html


def test_split_front_matter_tolerates_invalid_yaml():
    text = "---\n: bad\n---\n# Title\n"
    metadata, body = mpdf._split_front_matter(text)

    assert metadata == {}
    assert body == text


def test_build_html_document_includes_mermaid_script(tmp_path):
    markdown_file = tmp_path / "demo.md"
    markdown_file.write_text("```mermaid\ngraph TD\nA-->B\n```", encoding="utf-8")
    source = mpdf._load_markdown_source(markdown_file, tmp_path)

    html = mpdf._build_html_document(
        sources=[source],
        title="Demo",
        mermaid_script_source="file:///tmp/mermaid.min.js",
        enable_mermaid=True,
    )

    assert "mermaid.initialize" in html
    assert "file:///tmp/mermaid.min.js" in html


def test_resolve_bundled_mermaid_script_source_returns_file_uri():
    with ExitStack() as stack:
        script_uri = mpdf._resolve_mermaid_script_source(None, stack)
        assert script_uri.startswith("file:///")
        assert "mermaid.min.js" in script_uri


def test_convert_markdown_to_pdf_calls_browser_renderer(tmp_path, monkeypatch):
    markdown_file = tmp_path / "demo.md"
    markdown_file.write_text("# Demo\n\ncontent", encoding="utf-8")
    output_file = tmp_path / "demo.pdf"
    browser_path = tmp_path / "browser.exe"
    browser_path.write_text("", encoding="utf-8")
    rendered: dict[str, Path | int] = {}

    def fake_render(browser: Path, html_path: Path, output_path: Path, render_wait_ms: int) -> None:
        rendered["browser"] = browser
        rendered["html"] = html_path
        rendered["output"] = output_path
        rendered["wait"] = render_wait_ms
        output_path.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(mpdf, "_render_pdf_with_browser", fake_render)
    monkeypatch.setattr(mpdf, "_find_browser_executable", lambda _browser: browser_path.resolve())

    result = mpdf.convert_markdown_to_pdf(markdown_file, output_path=output_file)

    assert result == output_file.resolve()
    assert output_file.exists()
    assert rendered["browser"] == browser_path.resolve()
    assert Path(rendered["html"]).name == "document.html"
    assert rendered["wait"] == mpdf.DEFAULT_RENDER_WAIT_MS


def test_convert_markdown_to_pdf_rejects_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        mpdf.convert_markdown_to_pdf(tmp_path / "missing.md")


def test_wheel_contains_vendored_mermaid_assets():
    wheel_files = sorted(Path("dist").glob("zxtoolbox-*.whl"))
    if not wheel_files:
        pytest.skip("wheel file not built")

    wheel = wheel_files[-1]
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    assert "zxtoolbox/assets/mermaid/mermaid.min.js" in names
    assert "zxtoolbox/assets/mermaid/LICENSE" in names
