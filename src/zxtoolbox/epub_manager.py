"""EPUB to Markdown conversion utilities."""

from __future__ import annotations

import html
import io
import posixpath
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urldefrag
import xml.etree.ElementTree as ET
import zipfile
import zlib

from epublib import EPUB
from epublib.exceptions import EPUBError, NotEPUBError
from epublib.resources import Resource


DOCUMENT_MEDIA_TYPES = {
    "application/xhtml+xml",
    "text/html",
}

IMAGE_MEDIA_PREFIX = "image/"
BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "body",
    "chapter",
    "div",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "thead",
    "tfoot",
    "tr",
    "td",
    "th",
    "ul",
}
INLINE_BREAK_TAGS = {"br"}


@dataclass(frozen=True)
class ManifestItem:
    """A manifest item inside an EPUB package."""

    item_id: str
    href: str
    full_path: str
    media_type: str
    properties: frozenset[str]
    content: bytes


@dataclass(frozen=True)
class TocEntry:
    """A TOC entry extracted from the EPUB navigation structures."""

    title: str
    full_path: str
    fragment: str
    level: int


@dataclass(frozen=True)
class ChapterPlan:
    """A planned Markdown file for one spine document."""

    index: int
    item: ManifestItem
    title: str
    filename: str


@dataclass(frozen=True)
class EpubBook:
    """Parsed EPUB package metadata."""

    manifest: dict[str, ManifestItem]
    spine: list[ManifestItem]
    toc_entries: list[TocEntry]


def convert_epub_to_markdown(
    epub_file: str | Path,
    output_dir: str | Path | None = None,
    assets_dir_name: str = "assets",
    chapters_dir_name: str = "chapters",
    toc_filename: str = "toc.md",
) -> Path:
    """Convert an EPUB file into a Markdown directory structure.

    Output structure:
    - toc.md
    - chapters/*.md
    - assets/**/*
    """
    epub_path = Path(epub_file).resolve()
    if not epub_path.exists():
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")
    if not epub_path.is_file():
        raise ValueError(f"EPUB path is not a file: {epub_path}")

    book = _load_book(epub_path)
    chapter_items = [
        item for item in book.spine
        if item.media_type in DOCUMENT_MEDIA_TYPES
    ]
    if not chapter_items:
        raise ValueError("The EPUB file does not contain any readable chapter documents.")

    out_dir = Path(output_dir).resolve() if output_dir else epub_path.with_name(f"{epub_path.stem}_markdown")
    chapters_dir = out_dir / chapters_dir_name
    assets_dir = out_dir / assets_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    asset_output_map = _extract_assets(
        manifest=book.manifest,
        output_assets_dir=assets_dir,
        assets_dir_name=assets_dir_name,
    )

    title_map = _build_toc_title_map(book.toc_entries)
    plans = _build_chapter_plans(chapter_items, title_map)
    chapter_output_map = {
        plan.item.full_path: f"{chapters_dir_name}/{plan.filename}"
        for plan in plans
    }

    for plan in plans:
        markdown = _render_document(
            document_bytes=plan.item.content,
            current_document_path=plan.item.full_path,
            current_output_path=chapter_output_map[plan.item.full_path],
            chapter_output_map=chapter_output_map,
            asset_output_map=asset_output_map,
        ).strip()

        if not _starts_with_heading(markdown):
            markdown = f"# {plan.title}\n\n{markdown}" if markdown else f"# {plan.title}\n"

        (chapters_dir / plan.filename).write_text(f"{markdown.rstrip()}\n", encoding="utf-8")

    toc_path = out_dir / toc_filename
    toc_content = _build_toc_markdown(
        toc_entries=book.toc_entries,
        plans=plans,
        chapter_output_map=chapter_output_map,
    )
    toc_path.write_text(toc_content, encoding="utf-8")

    print(f"[OK] EPUB converted: {epub_path}")
    print(f"  output:   {out_dir}")
    print(f"  toc:      {toc_path}")
    print(f"  chapters: {len(plans)}")
    print(f"  assets:   {len(asset_output_map)}")
    return out_dir


def _load_book(epub_path: Path) -> EpubBook:
    """Load package metadata, manifest, spine, and TOC."""
    temp_epub_path: Path | None = None

    try:
        try:
            parsed_book = EPUB(epub_path)
        except NotEPUBError as exc:
            repaired_epub_path = _repair_epub_if_possible(epub_path)
            if repaired_epub_path is None:
                raise ValueError(f"Invalid EPUB file: {exc}") from exc
            temp_epub_path = repaired_epub_path
            parsed_book = EPUB(repaired_epub_path)

        manifest = _build_manifest(parsed_book)
        spine = _build_spine(parsed_book, manifest)
        toc_entries = _load_toc_entries(parsed_book)

        return EpubBook(
            manifest=manifest,
            spine=spine,
            toc_entries=toc_entries,
        )
    except (EPUBError, NotEPUBError, OSError, ET.ParseError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Invalid EPUB file: {exc}") from exc
    finally:
        if "parsed_book" in locals():
            parsed_book.close()
        if temp_epub_path is not None:
            try:
                temp_epub_path.unlink(missing_ok=True)
            except OSError:
                pass


def _build_manifest(parsed_book: EPUB) -> dict[str, ManifestItem]:
    """Build manifest items from epublib resources and metadata."""
    manifest: dict[str, ManifestItem] = {}

    for manifest_item in parsed_book.manifest.items:
        full_path = _normalize_posix_path("", str(manifest_item.filename))
        resource = _get_resource_by_filename(parsed_book, full_path)
        if resource is None:
            continue

        item = ManifestItem(
            item_id=str(manifest_item.id),
            href=str(manifest_item.href).replace("\\", "/"),
            full_path=full_path,
            media_type=str(manifest_item.media_type),
            properties=frozenset(manifest_item.properties or []),
            content=resource.content,
        )
        manifest[item.item_id] = item

    return manifest


def _build_spine(parsed_book: EPUB, manifest: dict[str, ManifestItem]) -> list[ManifestItem]:
    """Build the reading order from the EPUB spine."""
    spine: list[ManifestItem] = []

    for spine_item in parsed_book.spine.items:
        manifest_item = manifest.get(str(spine_item.idref))
        if manifest_item is not None:
            spine.append(manifest_item)

    return spine


def _load_toc_entries(parsed_book: EPUB) -> list[TocEntry]:
    """Load TOC entries from nav.xhtml or toc.ncx resources."""
    for manifest_item in parsed_book.manifest.items:
        if manifest_item.properties and "nav" in manifest_item.properties:
            full_path = _normalize_posix_path("", str(manifest_item.filename))
            resource = _get_resource_by_filename(parsed_book, full_path)
            if resource is not None:
                return _parse_nav_toc(resource.content, full_path)

    for manifest_item in parsed_book.manifest.items:
        if str(manifest_item.media_type) == "application/x-dtbncx+xml":
            full_path = _normalize_posix_path("", str(manifest_item.filename))
            resource = _get_resource_by_filename(parsed_book, full_path)
            if resource is not None:
                return _parse_ncx_toc(resource.content, full_path)

    return []


def _get_resource_by_filename(parsed_book: EPUB, filename: str) -> Resource | None:
    """Find a resource by filename while normalizing Windows path separators."""
    normalized_target = _normalize_posix_path("", filename)
    for resource in parsed_book.resources:
        resource_path = _normalize_posix_path("", resource.filename)
        if resource_path == normalized_target:
            return resource
    return None


def _parse_nav_toc(document_bytes: bytes, document_path: str) -> list[TocEntry]:
    """Parse a nav.xhtml table of contents."""
    root = ET.fromstring(document_bytes)
    toc_nav = None
    for element in root.iter():
        if _tag_name(element.tag) != "nav":
            continue
        nav_type = (
            element.attrib.get("{http://www.idpf.org/2007/ops}type")
            or element.attrib.get("epub:type")
            or element.attrib.get("type")
            or ""
        )
        if "toc" in nav_type or toc_nav is None:
            toc_nav = element
            if "toc" in nav_type:
                break

    if toc_nav is None:
        return []

    toc_entries: list[TocEntry] = []
    for child in toc_nav:
        if _tag_name(child.tag) not in {"ol", "ul"}:
            continue
        toc_entries.extend(_parse_nav_list(child, document_path, level=1))
    return toc_entries


def _parse_nav_list(list_element: ET.Element, document_path: str, level: int) -> list[TocEntry]:
    """Parse nested nav list items."""
    toc_entries: list[TocEntry] = []
    for item in list_element:
        if _tag_name(item.tag) != "li":
            continue

        label_element = None
        nested_list = None
        for child in item:
            tag_name = _tag_name(child.tag)
            if tag_name in {"a", "span"} and label_element is None:
                label_element = child
            elif tag_name in {"ol", "ul"} and nested_list is None:
                nested_list = child

        if label_element is not None:
            raw_title = _collapse_whitespace("".join(label_element.itertext()))
            href = label_element.attrib.get("href", "").strip()
            if raw_title and href:
                full_path, fragment = _resolve_reference(document_path, href)
                toc_entries.append(
                    TocEntry(
                        title=raw_title,
                        full_path=full_path,
                        fragment=fragment,
                        level=level,
                    )
                )

        if nested_list is not None:
            toc_entries.extend(_parse_nav_list(nested_list, document_path, level + 1))

    return toc_entries


def _parse_ncx_toc(document_bytes: bytes, document_path: str) -> list[TocEntry]:
    """Parse a toc.ncx table of contents."""
    root = ET.fromstring(document_bytes)
    nav_map = None
    for element in root.iter():
        if _tag_name(element.tag) == "navMap":
            nav_map = element
            break
    if nav_map is None:
        return []

    toc_entries: list[TocEntry] = []

    def visit(node: ET.Element, level: int) -> None:
        for child in node:
            if _tag_name(child.tag) != "navPoint":
                continue

            title = ""
            href = ""
            for item in child.iter():
                item_tag = _tag_name(item.tag)
                if item_tag == "text" and not title:
                    title = _collapse_whitespace("".join(item.itertext()))
                elif item_tag == "content" and not href:
                    href = item.attrib.get("src", "").strip()

            if title and href:
                full_path, fragment = _resolve_reference(document_path, href)
                toc_entries.append(
                    TocEntry(
                        title=title,
                        full_path=full_path,
                        fragment=fragment,
                        level=level,
                    )
                )

            visit(child, level + 1)

    visit(nav_map, level=1)
    return toc_entries


def _extract_assets(
    manifest: dict[str, ManifestItem],
    output_assets_dir: Path,
    assets_dir_name: str,
) -> dict[str, str]:
    """Extract static image assets and return EPUB-path to output-path mapping."""
    asset_output_map: dict[str, str] = {}

    for item in manifest.values():
        if not item.media_type.startswith(IMAGE_MEDIA_PREFIX):
            continue

        asset_relative = _sanitize_asset_relative_path(item.full_path)
        output_path = output_assets_dir / asset_relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(item.content)

        asset_output_map[item.full_path] = f"{assets_dir_name}/{Path(asset_relative).as_posix()}"

    return asset_output_map


def _sanitize_asset_relative_path(full_path: str) -> str:
    """Build a safe relative path for extracted assets."""
    relative = posixpath.normpath(full_path).lstrip("/")

    parts = []
    for part in relative.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            part = "parent"
        sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", part.strip()) or "asset"
        parts.append(sanitized)
    return "/".join(parts) or "asset"


def _build_toc_title_map(toc_entries: list[TocEntry]) -> dict[str, str]:
    """Map the first TOC title to each document path."""
    title_map: dict[str, str] = {}
    for entry in toc_entries:
        title_map.setdefault(entry.full_path, entry.title)
    return title_map


def _build_chapter_plans(
    chapter_items: list[ManifestItem],
    title_map: dict[str, str],
) -> list[ChapterPlan]:
    """Build deterministic filenames for all chapter documents."""
    used_slugs: set[str] = set()
    plans: list[ChapterPlan] = []

    for index, item in enumerate(chapter_items, start=1):
        title = title_map.get(item.full_path) or _extract_document_title(item.content)
        if not title:
            title = Path(item.href or item.full_path).stem

        slug = _unique_slug(_slugify(title), used_slugs, default=f"chapter-{index:02d}")
        filename = f"{index:02d}-{slug}.md"
        plans.append(
            ChapterPlan(
                index=index,
                item=item,
                title=title,
                filename=filename,
            )
        )

    return plans


def _extract_document_title(document_bytes: bytes) -> str:
    """Extract a fallback title from XHTML."""
    try:
        root = ET.fromstring(document_bytes)
    except ET.ParseError:
        return ""

    for element in root.iter():
        if _tag_name(element.tag) in {"h1", "h2", "h3", "title"}:
            title = _collapse_whitespace("".join(element.itertext()))
            if title:
                return title

    return ""


def _render_document(
    document_bytes: bytes,
    current_document_path: str,
    current_output_path: str,
    chapter_output_map: dict[str, str],
    asset_output_map: dict[str, str],
) -> str:
    """Render one XHTML document to Markdown."""
    root = ET.fromstring(document_bytes)
    body = root
    for element in root.iter():
        if _tag_name(element.tag) == "body":
            body = element
            break

    renderer = _MarkdownRenderer(
        current_document_path=current_document_path,
        current_output_path=current_output_path,
        chapter_output_map=chapter_output_map,
        asset_output_map=asset_output_map,
    )
    return renderer.render(body)


def _build_toc_markdown(
    toc_entries: list[TocEntry],
    plans: list[ChapterPlan],
    chapter_output_map: dict[str, str],
) -> str:
    """Build the top-level toc.md file."""
    lines = ["# Table of Contents", ""]

    if toc_entries:
        written = False
        for entry in toc_entries:
            chapter_target = chapter_output_map.get(entry.full_path)
            if chapter_target is None:
                continue

            link = chapter_target
            if entry.fragment:
                link = f"{link}#{entry.fragment}"
            indent = "  " * max(entry.level - 1, 0)
            lines.append(f"{indent}- [{entry.title}]({link})")
            written = True

        if written:
            lines.append("")
            return "\n".join(lines)

    for plan in plans:
        link = chapter_output_map[plan.item.full_path]
        lines.append(f"- [{plan.title}]({link})")

    lines.append("")
    return "\n".join(lines)


def _starts_with_heading(markdown: str) -> bool:
    """Check whether rendered Markdown starts with a heading after anchor lines."""
    normalized = markdown.lstrip()
    normalized = re.sub(r'^(<a id="[^"]+"></a>\s*)+', "", normalized)
    return normalized.startswith("#")


class _MarkdownRenderer:
    """A lightweight XHTML to Markdown renderer."""

    def __init__(
        self,
        current_document_path: str,
        current_output_path: str,
        chapter_output_map: dict[str, str],
        asset_output_map: dict[str, str],
    ) -> None:
        self.current_document_path = current_document_path
        self.current_output_path = current_output_path
        self.chapter_output_map = chapter_output_map
        self.asset_output_map = asset_output_map

    def render(self, element: ET.Element) -> str:
        """Render the given body element into Markdown."""
        blocks = self._render_children_as_blocks(element)
        return "\n\n".join(block for block in blocks if block.strip()).strip()

    def _render_children_as_blocks(self, element: ET.Element) -> list[str]:
        blocks: list[str] = []

        direct_text = _collapse_whitespace(element.text or "")
        if direct_text and self._contains_block_children(element):
            blocks.append(direct_text)

        for child in element:
            tag_name = _tag_name(child.tag)
            rendered = self._render_block(child)
            if rendered:
                blocks.append(rendered)
            elif tag_name not in BLOCK_TAGS:
                inline_text = self._render_inline(child).strip()
                if inline_text:
                    blocks.append(inline_text)

            tail = _collapse_whitespace(child.tail or "")
            if tail:
                blocks.append(tail)

        if not blocks and not self._contains_block_children(element):
            inline_text = self._render_inline(element).strip()
            if inline_text:
                blocks.append(inline_text)

        return blocks

    def _render_block(self, element: ET.Element) -> str:
        tag_name = _tag_name(element.tag)
        anchor_prefix = self._anchor_prefix(element)

        if tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag_name[1])
            content = self._render_inline(element).strip()
            if not content:
                return anchor_prefix.rstrip()
            return f"{anchor_prefix}{'#' * level} {content}".strip()

        if tag_name == "p":
            content = self._render_inline(element).strip()
            return f"{anchor_prefix}{content}".strip()

        if tag_name == "blockquote":
            content = self._render_inline(element).strip()
            if not content:
                content = "\n\n".join(self._render_children_as_blocks(element))
            quoted = "\n".join(f"> {line}" if line else ">" for line in content.splitlines())
            return f"{anchor_prefix}{quoted}".strip()

        if tag_name == "pre":
            content = "".join(element.itertext()).rstrip()
            if not content:
                return anchor_prefix.rstrip()
            return f"{anchor_prefix}```\n{content}\n```".strip()

        if tag_name in {"ul", "ol"}:
            return f"{anchor_prefix}{self._render_list(element, ordered=(tag_name == 'ol'), depth=0)}".strip()

        if tag_name == "img":
            content = self._render_image(element)
            return f"{anchor_prefix}{content}".strip()

        if tag_name == "hr":
            return f"{anchor_prefix}---".strip()

        if tag_name == "table":
            raw_html = ET.tostring(element, encoding="unicode")
            return f"{anchor_prefix}{raw_html}".strip()

        if tag_name in {"div", "section", "article", "body", "main", "figure", "nav", "aside", "chapter"}:
            child_blocks = self._render_children_as_blocks(element)
            if child_blocks:
                content = "\n\n".join(child_blocks)
                return f"{anchor_prefix}{content}".strip()
            content = self._render_inline(element).strip()
            return f"{anchor_prefix}{content}".strip()

        if tag_name == "li":
            return self._render_list_item(element, ordered=False, depth=0, index=1)

        return ""

    def _render_list(self, element: ET.Element, ordered: bool, depth: int) -> str:
        lines: list[str] = []
        counter = 1
        for child in element:
            if _tag_name(child.tag) != "li":
                continue
            rendered = self._render_list_item(child, ordered=ordered, depth=depth, index=counter)
            if rendered:
                lines.append(rendered)
            if ordered:
                counter += 1
        return "\n".join(lines).rstrip()

    def _render_list_item(self, element: ET.Element, ordered: bool, depth: int, index: int) -> str:
        indent = "    " * depth
        marker = f"{index}. " if ordered else "- "
        anchor_prefix = self._anchor_prefix(element).strip()

        inline_parts: list[str] = []
        nested_lists: list[str] = []

        if element.text and element.text.strip():
            inline_parts.append(_collapse_whitespace(element.text))

        for child in element:
            child_tag = _tag_name(child.tag)
            if child_tag in {"ul", "ol"}:
                nested = self._render_list(child, ordered=(child_tag == "ol"), depth=depth + 1)
                if nested:
                    nested_lists.append(nested)
            elif child_tag in BLOCK_TAGS and child_tag not in {"ul", "ol"}:
                block = self._render_block(child).strip()
                if block:
                    inline_parts.append(block)
            else:
                inline_parts.append(self._render_inline_tag(child))

            if child.tail and child.tail.strip():
                inline_parts.append(_collapse_whitespace(child.tail))

        line_body = "".join(inline_parts).strip()
        if anchor_prefix:
            line_body = f"{anchor_prefix} {line_body}".strip()

        if not line_body:
            line_body = anchor_prefix

        lines = [f"{indent}{marker}{line_body}".rstrip()]
        for nested in nested_lists:
            lines.append(nested)
        return "\n".join(lines)

    def _render_inline(self, element: ET.Element) -> str:
        parts: list[str] = []
        if element.text:
            parts.append(_normalize_inline_text(element.text))

        for child in element:
            parts.append(self._render_inline_tag(child))
            if child.tail:
                parts.append(_normalize_inline_text(child.tail))

        return "".join(parts).strip()

    def _render_inline_tag(self, element: ET.Element) -> str:
        tag_name = _tag_name(element.tag)

        if tag_name in {"strong", "b"}:
            content = self._render_inline(element).strip()
            return f"**{content}**" if content else ""

        if tag_name in {"em", "i"}:
            content = self._render_inline(element).strip()
            return f"*{content}*" if content else ""

        if tag_name == "code":
            content = self._render_inline(element).strip()
            return f"`{content}`" if content else ""

        if tag_name in INLINE_BREAK_TAGS:
            return "  \n"

        if tag_name == "a":
            content = self._render_inline(element).strip() or element.attrib.get("href", "").strip()
            href = element.attrib.get("href", "").strip()
            rewritten = self._rewrite_reference(href)
            return f"[{content}]({rewritten})" if rewritten else content

        if tag_name == "img":
            return self._render_image(element)

        if tag_name in BLOCK_TAGS:
            return self._render_inline(element)

        return self._render_inline(element)

    def _render_image(self, element: ET.Element) -> str:
        src = element.attrib.get("src", "").strip()
        if not src:
            return ""

        alt = _collapse_whitespace(element.attrib.get("alt", "")) or Path(src).stem
        rewritten = self._rewrite_reference(src)
        return f"![{alt}]({rewritten})"

    def _rewrite_reference(self, reference: str) -> str:
        if not reference:
            return ""
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", reference):
            return reference

        resolved_path, fragment = _resolve_reference(self.current_document_path, reference)

        if resolved_path in self.asset_output_map:
            target = self.asset_output_map[resolved_path]
            relative = posixpath.relpath(target, posixpath.dirname(self.current_output_path) or ".")
            return f"{relative}#{fragment}" if fragment else relative

        if resolved_path in self.chapter_output_map:
            target = self.chapter_output_map[resolved_path]
            relative = posixpath.relpath(target, posixpath.dirname(self.current_output_path) or ".")
            return f"{relative}#{fragment}" if fragment else relative

        if not resolved_path and fragment:
            return f"#{fragment}"

        return reference

    def _anchor_prefix(self, element: ET.Element) -> str:
        element_id = element.attrib.get("id", "").strip()
        if not element_id:
            return ""
        return f'<a id="{html.escape(element_id, quote=True)}"></a>\n'

    @staticmethod
    def _contains_block_children(element: ET.Element) -> bool:
        return any(_tag_name(child.tag) in BLOCK_TAGS for child in element)


def _normalize_posix_path(base_dir: str, href: str) -> str:
    """Normalize a POSIX path relative to the OPF or current document."""
    return posixpath.normpath(posixpath.join(base_dir or ".", href.replace("\\", "/")))


def _resolve_reference(document_path: str, reference: str) -> tuple[str, str]:
    """Resolve a document-relative href into a normalized EPUB path and fragment."""
    path_part, fragment = urldefrag(reference)
    if not path_part:
        return document_path, fragment
    resolved = _normalize_posix_path(posixpath.dirname(document_path), path_part)
    return resolved, fragment


def _tag_name(tag: str) -> str:
    """Strip namespaces from XML tag names."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _collapse_whitespace(text: str) -> str:
    """Collapse internal whitespace while preserving Markdown readability."""
    return re.sub(r"\s+", " ", text).strip()


def _normalize_inline_text(text: str) -> str:
    """Collapse whitespace but preserve a single leading/trailing blank when present."""
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", text)
    if not collapsed.strip():
        return " "
    prefix = " " if collapsed[0].isspace() else ""
    suffix = " " if collapsed[-1].isspace() else ""
    return f"{prefix}{collapsed.strip()}{suffix}"


def _slugify(text: str) -> str:
    """Generate an ASCII slug from a chapter title."""
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return normalized


def _unique_slug(slug: str, used_slugs: set[str], default: str) -> str:
    """Ensure chapter filename slugs are unique."""
    candidate = slug or default
    index = 2
    base = candidate
    while candidate in used_slugs:
        candidate = f"{base}-{index}"
        index += 1
    used_slugs.add(candidate)
    return candidate


def _repair_epub_if_possible(epub_path: Path) -> Path | None:
    """Rebuild a readable ZIP from local file headers when the central directory is broken."""
    entries = _scan_local_file_entries(epub_path)
    if not entries:
        return None

    names = {entry.filename for entry in entries}
    if "META-INF/container.xml" not in names or "mimetype" not in names:
        return None

    workspace_temp_root = epub_path.parent / "dist" / "epub_repair"
    workspace_temp_root.mkdir(parents=True, exist_ok=True)
    temp_epub_path = workspace_temp_root / f"{epub_path.stem}.repaired.epub"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        ordered_entries = sorted(
            entries,
            key=lambda entry: (
                0 if entry.filename == "mimetype" else 1,
                entry.offset,
            ),
        )
        for entry in ordered_entries:
            compress_type = zipfile.ZIP_STORED if entry.compression_method == 0 else zipfile.ZIP_DEFLATED
            archive.writestr(entry.filename, entry.data, compress_type=compress_type)

    temp_epub_path.write_bytes(buffer.getvalue())
    return temp_epub_path


@dataclass(frozen=True)
class _LocalZipEntry:
    """A ZIP member parsed from a local file header."""

    filename: str
    compression_method: int
    data: bytes
    offset: int


def _scan_local_file_entries(epub_path: Path) -> list[_LocalZipEntry]:
    """Scan ZIP local file headers without relying on the central directory."""
    data = epub_path.read_bytes()
    size = len(data)
    offset = 0
    entries: list[_LocalZipEntry] = []
    seen_names: set[str] = set()

    while offset + 30 <= size:
        if data[offset:offset + 4] != b"PK\x03\x04":
            offset += 1
            continue

        try:
            (
                _version,
                flag_bits,
                compression_method,
                _mod_time,
                _mod_date,
                _crc,
                compressed_size,
                _uncompressed_size,
                filename_length,
                extra_length,
            ) = struct.unpack_from("<HHHHHIIIHH", data, offset + 4)
        except struct.error:
            break

        if flag_bits & 0x08:
            return []

        header_end = offset + 30
        filename_end = header_end + filename_length
        extra_end = filename_end + extra_length
        data_end = extra_end + compressed_size
        if data_end > size:
            break

        raw_filename = data[header_end:filename_end]
        try:
            encoding = "utf-8" if flag_bits & 0x800 else "cp437"
            filename = raw_filename.decode(encoding)
        except UnicodeDecodeError:
            offset += 1
            continue

        if filename.endswith("/"):
            offset = data_end
            continue

        payload = data[extra_end:data_end]

        try:
            if compression_method == 0:
                entry_data = payload
            elif compression_method == 8:
                entry_data = zlib.decompress(payload, -15)
            else:
                offset = data_end
                continue
        except Exception:
            offset += 1
            continue

        normalized_name = filename.replace("\\", "/")
        if normalized_name not in seen_names:
            entries.append(
                _LocalZipEntry(
                    filename=normalized_name,
                    compression_method=compression_method,
                    data=entry_data,
                    offset=offset,
                )
            )
            seen_names.add(normalized_name)

        offset = data_end

    return entries
