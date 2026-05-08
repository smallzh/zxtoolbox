"""Markdown to PDF conversion utilities."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import html
from importlib import resources
import locale
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import urldefrag

import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
import yaml


BUNDLED_MERMAID_RESOURCE = ("assets", "mermaid", "mermaid.min.js")
DEFAULT_RENDER_WAIT_MS = 5000
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}
HEADING_RE = re.compile(r"^\s{0,3}#\s+(?P<title>.+?)\s*(?:#+\s*)?$", re.MULTILINE)
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(?P<meta>.*?)\n---[ \t]*\n?", re.DOTALL)
LOCAL_URL_RE = re.compile(
    r'(?P<attr>\b(?:src|href)\s*=\s*)(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.IGNORECASE,
)
MERMAID_FENCE_RE = re.compile(
    r"(?P<indent>^[ \t]*)(?P<fence>`{3,}|~{3,})[ \t]*mermaid[^\n]*\n"
    r"(?P<code>.*?)(?:\n(?P=indent)(?P=fence)[ \t]*(?=\n|$))",
    re.MULTILINE | re.DOTALL,
)


BASE_CSS = """
@page {
    size: A4;
    margin: 16mm 14mm 18mm;
}

:root {
    color-scheme: light;
    --text: #1f2937;
    --muted: #6b7280;
    --border: #d1d5db;
    --border-soft: #e5e7eb;
    --code-bg: #f3f4f6;
    --quote-bg: #f8fafc;
    --accent: #2563eb;
    --heading: #111827;
    --admonition-note: #dbeafe;
    --admonition-warn: #fef3c7;
    --admonition-danger: #fee2e2;
}

* {
    box-sizing: border-box;
}

html {
    font-size: 15px;
}

body {
    margin: 0;
    color: var(--text);
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.7;
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

main {
    width: 100%;
}

article.document {
    page-break-before: auto;
}

article.document + article.document {
    page-break-before: always;
}

.document-path {
    margin: 0 0 1rem;
    color: var(--muted);
    font-size: 0.88rem;
    letter-spacing: 0.02em;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--heading);
    line-height: 1.25;
    margin: 1.4em 0 0.65em;
    page-break-after: avoid;
}

h1 {
    font-size: 1.8rem;
    border-bottom: 1px solid var(--border-soft);
    padding-bottom: 0.35rem;
}

h2 {
    font-size: 1.45rem;
    border-bottom: 1px solid var(--border-soft);
    padding-bottom: 0.25rem;
}

h3 {
    font-size: 1.2rem;
}

p, ul, ol, table, blockquote, pre {
    margin: 0 0 1rem;
}

ul, ol {
    padding-left: 1.5rem;
}

li + li {
    margin-top: 0.2rem;
}

a {
    color: var(--accent);
    text-decoration: none;
}

img {
    max-width: 100%;
    height: auto;
}

hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

code {
    font-family: "Cascadia Code", "JetBrains Mono", Consolas, monospace;
    background: var(--code-bg);
    padding: 0.12rem 0.32rem;
    border-radius: 0.25rem;
    font-size: 0.92em;
}

pre {
    background: var(--code-bg);
    padding: 0.9rem 1rem;
    border-radius: 0.4rem;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

pre code {
    background: transparent;
    padding: 0;
}

blockquote {
    margin-left: 0;
    padding: 0.7rem 1rem;
    border-left: 4px solid var(--border);
    background: var(--quote-bg);
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.96rem;
}

th, td {
    border: 1px solid var(--border);
    padding: 0.55rem 0.65rem;
    text-align: left;
    vertical-align: top;
}

thead th {
    background: #f9fafb;
}

.admonition {
    margin: 0 0 1rem;
    padding: 0.9rem 1rem;
    border-left: 4px solid var(--accent);
    background: #eff6ff;
    border-radius: 0.35rem;
}

.admonition .admonition-title {
    margin: 0 0 0.4rem;
    font-weight: 700;
}

.admonition.warning,
.admonition.caution {
    background: var(--admonition-warn);
    border-left-color: #d97706;
}

.admonition.danger,
.admonition.error {
    background: var(--admonition-danger);
    border-left-color: #dc2626;
}

.admonition.note,
.admonition.info,
.admonition.tip {
    background: var(--admonition-note);
}

.mermaid {
    text-align: center;
    margin: 1rem 0;
}

.mermaid svg {
    max-width: 100%;
    height: auto;
}
"""


@dataclass(frozen=True)
class MarkdownSource:
    """One Markdown document participating in a PDF export."""

    path: Path
    relative_path: Path
    title: str
    content: str


class _MermaidFencePreprocessor(Preprocessor):
    """Convert mermaid fenced code blocks into mermaid containers."""

    def run(self, lines: list[str]) -> list[str]:
        text = "\n".join(lines)

        def replace(match: re.Match[str]) -> str:
            code = match.group("code").strip("\n")
            return f'{match.group("indent")}<div class="mermaid">\n{code}\n{match.group("indent")}</div>'

        return MERMAID_FENCE_RE.sub(replace, text).splitlines()


class MermaidExtension(Extension):
    """Markdown extension for Mermaid fenced code blocks."""

    def extendMarkdown(self, md: markdown.Markdown) -> None:  # noqa: N802
        md.preprocessors.register(_MermaidFencePreprocessor(md), "zxtool_mermaid", 26)


def convert_markdown_to_pdf(
    input_path: str | Path,
    output_path: str | Path | None = None,
    title: str | None = None,
    directory_file: str | Path = "README.md",
    browser_path: str | Path | None = None,
    mermaid_js: str | None = None,
    enable_mermaid: bool = True,
    render_wait_ms: int = DEFAULT_RENDER_WAIT_MS,
) -> Path:
    """Convert one Markdown file or directory into a PDF file."""
    source_path = Path(input_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"input path not found: {source_path}")

    output_file = _resolve_output_path(source_path, output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sources, document_title = _collect_markdown_sources(
        source_path,
        title=title,
        directory_file=directory_file,
    )
    browser = _find_browser_executable(browser_path)
    with ExitStack() as stack:
        mermaid_script_source: str | None = None
        if enable_mermaid and any(_contains_mermaid_block(source.content) for source in sources):
            mermaid_script_source = _resolve_mermaid_script_source(mermaid_js, stack)

        with tempfile.TemporaryDirectory(prefix="zxtool_mkpdf_") as temp_dir:
            html_path = Path(temp_dir) / "document.html"
            document_html = _build_html_document(
                sources=sources,
                title=document_title,
                mermaid_script_source=mermaid_script_source,
                enable_mermaid=enable_mermaid,
            )
            html_path.write_text(document_html, encoding="utf-8")
            _render_pdf_with_browser(
                browser=browser,
                html_path=html_path,
                output_path=output_file,
                render_wait_ms=render_wait_ms,
            )

    print(f"[OK] PDF generated: {output_file}")
    print(f"  source:  {source_path}")
    print(f"  browser: {browser}")
    print(f"  files:   {len(sources)}")
    return output_file


def _collect_markdown_sources(
    input_path: Path,
    title: str | None = None,
    directory_file: str | Path = "README.md",
) -> tuple[list[MarkdownSource], str]:
    """Collect Markdown sources from one file or one directory."""
    if input_path.is_file():
        if input_path.suffix.lower() not in MARKDOWN_SUFFIXES:
            raise ValueError("input file must be a Markdown file")
        source = _load_markdown_source(input_path, input_path.parent)
        return [source], title or source.title

    if not input_path.is_dir():
        raise ValueError(f"input path is neither file nor directory: {input_path}")

    markdown_path = _resolve_directory_markdown_file(input_path, directory_file)
    source = _load_markdown_source(markdown_path, input_path)
    return [source], title or source.title


def _resolve_directory_markdown_file(input_dir: Path, directory_file: str | Path) -> Path:
    """Resolve the entry Markdown file inside one input directory."""
    candidate = Path(directory_file)
    if candidate.is_absolute():
        markdown_path = candidate.resolve()
    else:
        markdown_path = (input_dir / candidate).resolve()

    try:
        markdown_path.relative_to(input_dir.resolve())
    except ValueError as exc:
        raise ValueError("directory file must stay within the input directory") from exc

    if not markdown_path.exists():
        raise FileNotFoundError(f"directory entry Markdown file not found: {markdown_path}")
    if not markdown_path.is_file():
        raise ValueError(f"directory entry path is not a file: {markdown_path}")
    if markdown_path.suffix.lower() not in MARKDOWN_SUFFIXES:
        raise ValueError("directory entry file must be a Markdown file")
    return markdown_path


def _load_markdown_source(markdown_path: Path, base_root: Path) -> MarkdownSource:
    """Load one Markdown file and derive title metadata."""
    try:
        raw_text = markdown_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"failed to read Markdown file as UTF-8: {markdown_path}") from exc

    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    metadata, body = _split_front_matter(raw_text)
    relative_path = markdown_path.resolve().relative_to(base_root.resolve())
    source_title = _extract_title(body, metadata, fallback=markdown_path.stem)
    return MarkdownSource(
        path=markdown_path.resolve(),
        relative_path=relative_path,
        title=source_title,
        content=body,
    )


def _build_html_document(
    sources: list[MarkdownSource],
    title: str,
    mermaid_script_source: str | None,
    enable_mermaid: bool,
) -> str:
    """Build one printable HTML document for all Markdown sources."""
    has_multiple_documents = len(sources) > 1
    needs_mermaid = enable_mermaid and mermaid_script_source is not None

    body_parts: list[str] = []

    for source in sources:
        body_parts.append('<article class="document">')
        if has_multiple_documents:
            body_parts.append(
                f'<p class="document-path">{html.escape(source.relative_path.as_posix())}</p>'
            )
        body_parts.append(
            _render_markdown_html(
                source=source,
                enable_mermaid=needs_mermaid,
            )
        )
        body_parts.append("</article>")

    mermaid_script = _build_mermaid_script(mermaid_script_source) if needs_mermaid else ""
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{html.escape(title)}</title>",
            "  <style>",
            BASE_CSS.strip(),
            "  </style>",
            mermaid_script,
            "</head>",
            "<body>",
            "<main>",
            "\n".join(body_parts),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _render_markdown_html(source: MarkdownSource, enable_mermaid: bool) -> str:
    """Render one Markdown document to HTML."""
    extensions: list[str | Extension] = [
        "extra",
        "admonition",
        "attr_list",
        "md_in_html",
        "sane_lists",
    ]
    if enable_mermaid:
        extensions.append(MermaidExtension())

    rendered = markdown.markdown(
        source.content,
        extensions=extensions,
        output_format="html5",
    )
    return _rewrite_local_urls(rendered, source.path.parent)


def _rewrite_local_urls(rendered_html: str, base_dir: Path) -> str:
    """Rewrite local HTML href/src attributes to absolute file URLs."""

    def replace(match: re.Match[str]) -> str:
        raw_value = html.unescape(match.group("value"))
        rewritten = _rewrite_local_reference(raw_value, base_dir)
        escaped = html.escape(rewritten, quote=True)
        return f"{match.group('attr')}{match.group('quote')}{escaped}{match.group('quote')}"

    return LOCAL_URL_RE.sub(replace, rendered_html)


def _rewrite_local_reference(reference: str, base_dir: Path) -> str:
    """Rewrite one local reference to a file:// URL when possible."""
    reference = reference.strip()
    if not reference or reference.startswith("#") or reference.startswith("//"):
        return reference
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", reference):
        return reference

    relative_path, fragment = urldefrag(reference)
    target = (base_dir / relative_path).resolve()
    if not target.exists():
        return reference

    rewritten = target.as_uri()
    if fragment:
        rewritten = f"{rewritten}#{fragment}"
    return rewritten


def _build_mermaid_script(script_source: str) -> str:
    """Build Mermaid script tags."""
    escaped_source = html.escape(script_source, quote=True)
    return "\n".join(
        [
            f'  <script src="{escaped_source}"></script>',
            "  <script>",
            "    window.addEventListener('load', async () => {",
            "      if (!window.mermaid) {",
            "        return;",
            "      }",
            "      try {",
            "        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', theme: 'default' });",
            "        await mermaid.run({ querySelector: '.mermaid' });",
            "      } catch (error) {",
            "        console.error('Failed to render Mermaid diagrams.', error);",
            "      }",
            "    });",
            "  </script>",
        ]
    )


def _resolve_mermaid_script_source(mermaid_js: str | None, stack: ExitStack) -> str:
    """Resolve Mermaid script source to either URL or local file URI."""
    if mermaid_js is None:
        resource = resources.files("zxtoolbox").joinpath(*BUNDLED_MERMAID_RESOURCE)
        return stack.enter_context(resources.as_file(resource)).as_uri()
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", mermaid_js):
        return mermaid_js

    mermaid_path = Path(mermaid_js).expanduser().resolve()
    if not mermaid_path.exists():
        raise FileNotFoundError(f"mermaid script not found: {mermaid_path}")
    return mermaid_path.as_uri()


def _render_pdf_with_browser(
    browser: Path,
    html_path: Path,
    output_path: Path,
    render_wait_ms: int,
) -> None:
    """Render HTML to PDF using a Chromium-compatible browser."""
    if render_wait_ms < 0:
        raise ValueError("render_wait_ms must be >= 0")

    command = [
        str(browser),
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-dev-shm-usage",
        "--disable-features=RendererCodeIntegrity",
        "--no-first-run",
        "--disable-extensions",
        "--allow-file-access-from-files",
        "--disable-web-security",
        f"--virtual-time-budget={render_wait_ms}",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={output_path}",
        html_path.as_uri(),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=False,
        check=False,
    )
    stderr = _decode_process_output(result.stderr).strip()
    stdout = _decode_process_output(result.stdout).strip()
    if result.returncode != 0:
        error = stderr or stdout or "unknown error"
        raise RuntimeError(f"browser PDF export failed: {error}")
    if not output_path.exists():
        error = stderr or stdout
        if error:
            raise RuntimeError(f"browser completed without creating the PDF file: {error}")
        raise RuntimeError("browser completed without creating the PDF file")


def _decode_process_output(output: bytes | None) -> str:
    """Decode subprocess output without relying on the Windows console code page."""
    if not output:
        return ""

    encodings = ["utf-8", locale.getpreferredencoding(False)]
    for encoding in dict.fromkeys(encodings):
        if not encoding:
            continue
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue
    return output.decode("utf-8", errors="replace")


def _find_browser_executable(browser_path: str | Path | None) -> Path:
    """Find a Chromium-compatible browser executable."""
    if browser_path is not None:
        explicit = str(browser_path)
        which_path = shutil.which(explicit)
        resolved = Path(which_path or explicit).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"browser executable not found: {resolved}")
        return resolved

    candidates: list[str] = []
    if os.name == "nt":
        candidates.extend(
            [
                "msedge",
                "chrome",
                "chromium",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Chromium\Application\chrome.exe",
                r"C:\Program Files (x86)\Chromium\Application\chrome.exe",
            ]
        )
    elif sys.platform == "darwin":
        candidates.extend(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "google-chrome",
                "microsoft-edge",
                "chromium",
            ]
        )
    else:
        candidates.extend(
            [
                "google-chrome",
                "google-chrome-stable",
                "microsoft-edge",
                "chromium",
                "chromium-browser",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/snap/bin/chromium",
            ]
        )

    for candidate in candidates:
        path = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if path:
            resolved = Path(path).expanduser().resolve()
            if resolved.exists():
                return resolved

    raise FileNotFoundError(
        "no Chromium-compatible browser found; install Edge/Chrome/Chromium or pass --browser"
    )


def _resolve_output_path(input_path: Path, output_path: str | Path | None) -> Path:
    """Resolve output PDF path."""
    default_name = f"{input_path.stem}.pdf" if input_path.is_file() else f"{input_path.name}.pdf"

    if output_path is None:
        if input_path.is_file():
            return input_path.with_suffix(".pdf").resolve()
        return (input_path.parent / default_name).resolve()

    resolved = Path(output_path).expanduser()
    if resolved.exists() and resolved.is_dir():
        return (resolved / default_name).resolve()
    if resolved.suffix.lower() != ".pdf":
        resolved = resolved.with_suffix(".pdf")
    return resolved.resolve()


def _split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML front matter from Markdown body."""
    match = FRONT_MATTER_RE.match(text)
    if match is None:
        return {}, text

    raw_front_matter = match.group("meta")
    body = text[match.end():]
    try:
        metadata = yaml.safe_load(raw_front_matter) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, body


def _extract_title(text: str, metadata: dict[str, Any], fallback: str) -> str:
    """Extract a document title from front matter or first heading."""
    meta_title = metadata.get("title")
    if isinstance(meta_title, str) and meta_title.strip():
        return meta_title.strip()

    match = HEADING_RE.search(text)
    if match:
        return _strip_markdown_inline(match.group("title"))
    return fallback


def _strip_markdown_inline(value: str) -> str:
    """Strip common inline Markdown markers from a heading title."""
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    value = re.sub(r"_([^_]+)_", r"\1", value)
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return value.strip()


def _contains_mermaid_block(text: str) -> bool:
    """Check whether Markdown contains Mermaid fenced blocks."""
    return bool(MERMAID_FENCE_RE.search(text))
