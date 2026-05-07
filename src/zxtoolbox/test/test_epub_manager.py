"""Tests for zxtoolbox.epub_manager."""

from __future__ import annotations

import zipfile
from pathlib import Path

from zxtoolbox.epub_manager import convert_epub_to_markdown


def _write_sample_epub(epub_path: Path) -> None:
    with zipfile.ZipFile(epub_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="text/chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="text/chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="image1" href="images/pic.png" media-type="image/png"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
  </spine>
</package>
""",
        )
        archive.writestr(
            "OEBPS/nav.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <body>
    <nav epub:type="toc">
      <ol>
        <li><a href="text/chapter1.xhtml">Chapter One</a></li>
        <li><a href="text/chapter2.xhtml#part-two">Chapter Two</a></li>
      </ol>
    </nav>
  </body>
</html>
""",
        )
        archive.writestr(
            "OEBPS/text/chapter1.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <h1 id="intro">Intro</h1>
    <p>Hello <strong>world</strong>.</p>
    <p><img src="../images/pic.png" alt="Picture"/></p>
  </body>
</html>
""",
        )
        archive.writestr(
            "OEBPS/text/chapter2.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <h2 id="part-two">Part Two</h2>
    <p><a href="chapter1.xhtml#intro">Back to intro</a></p>
  </body>
</html>
""",
        )
        archive.writestr("OEBPS/images/pic.png", b"PNGDATA")


def test_convert_epub_to_markdown_creates_expected_structure(tmp_path):
    epub_path = tmp_path / "book.epub"
    output_dir = tmp_path / "book_out"
    _write_sample_epub(epub_path)

    result = convert_epub_to_markdown(epub_path, output_dir=output_dir)

    assert result == output_dir.resolve()
    toc_path = output_dir / "toc.md"
    chapter1_path = output_dir / "chapters" / "01-chapter-one.md"
    chapter2_path = output_dir / "chapters" / "02-chapter-two.md"
    asset_path = output_dir / "assets" / "images" / "pic.png"

    assert toc_path.exists()
    assert chapter1_path.exists()
    assert chapter2_path.exists()
    assert asset_path.exists()

    toc_text = toc_path.read_text(encoding="utf-8")
    chapter1_text = chapter1_path.read_text(encoding="utf-8")
    chapter2_text = chapter2_path.read_text(encoding="utf-8")

    assert "[Chapter One](chapters/01-chapter-one.md)" in toc_text
    assert "[Chapter Two](chapters/02-chapter-two.md#part-two)" in toc_text
    assert "# Intro" in chapter1_text
    assert "Hello **world**." in chapter1_text
    assert "![Picture](../assets/images/pic.png)" in chapter1_text
    assert '<a id="part-two"></a>' in chapter2_text
    assert "[Back to intro](01-chapter-one.md#intro)" in chapter2_text
