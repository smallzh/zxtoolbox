## ADDED Requirements

### Requirement: EPUB parsing
Uses the epublib library to load and parse EPUB package documents.

#### Scenario: Loads EPUB file successfully
- **WHEN** a valid EPUB file path is provided
- **THEN** the EPUB is parsed using epublib
- **AND** the book metadata (title, author, etc.) is extracted

#### Scenario: Errors on invalid EPUB
- **WHEN** the provided file is not a valid EPUB (not a ZIP or missing required files)
- **THEN** a descriptive error is raised indicating the file is not a valid EPUB

### Requirement: Chapter extraction
Splits each spine document (XHTML file) from the EPUB into individual Markdown files.

#### Scenario: Extracts each spine item to a separate Markdown file
- **WHEN** the EPUB is parsed
- **THEN** each document in the spine is converted to Markdown
- **AND** saved as a separate `.md` file, named after the chapter title or spine index

#### Scenario: Preserves chapter order
- **WHEN** chapter files are written
- **THEN** filenames are prefixed with a zero-padded index to preserve the original spine order

### Requirement: Asset extraction
Extracts images and other binary assets from the EPUB to an `assets/` directory.

#### Scenario: Extracts images from EPUB
- **WHEN** the EPUB contains image files (JPEG, PNG, GIF, SVG)
- **THEN** they are extracted to an `assets/` subdirectory alongside the Markdown output

#### Scenario: Preserves directory structure for assets
- **WHEN** asset extraction occurs
- **THEN** relative paths within the EPUB are preserved (e.g., `images/photo.jpg` stays in `assets/images/photo.jpg`)

#### Scenario: Updates image references in Markdown
- **WHEN** image references exist in the Markdown output
- **THEN** the paths are updated to point to the extracted `assets/` directory

### Requirement: TOC generation
Generates a `toc.md` file from the EPUB's table of contents (nav.xhtml or toc.ncx).

#### Scenario: Generates TOC from nav.xhtml
- **WHEN** the EPUB contains a `nav.xhtml` navigation document
- **THEN** a `toc.md` file is generated with a hierarchical list of links to each chapter

#### Scenario: Falls back to toc.ncx
- **WHEN** the EPUB does not contain `nav.xhtml` but has `toc.ncx`
- **THEN** the navigation points from `toc.ncx` are used to generate the table of contents

#### Scenario: Creates nested TOC for multi-level navigation
- **WHEN** the EPUB navigation has nested headings
- **THEN** the TOC preserves the hierarchy with indentation or sub-lists in Markdown

### Requirement: XHTML to Markdown
A custom renderer converts XHTML content to Markdown while preserving formatting (headings, lists, links, images, bold, italic, code blocks, tables).

#### Scenario: Converts headings
- **WHEN** an XHTML document contains `<h1>` through `<h6>` elements
- **THEN** they are converted to the corresponding Markdown `#` heading syntax

#### Scenario: Converts lists
- **WHEN** an XHTML document contains `<ul>` or `<ol>` elements
- **THEN** unordered lists become `- ` items and ordered lists become `1. ` numbered items

#### Scenario: Converts links and images
- **WHEN** an XHTML document contains `<a>` or `<img>` elements
- **THEN** links become `[text](url)` and images become `![alt](src)` in Markdown

#### Scenario: Converts tables
- **WHEN** an XHTML document contains `<table>`, `<tr>`, `<th>`, `<td>` elements
- **THEN** they are converted to Markdown pipe-table syntax

#### Scenario: Preserves inline formatting
- **WHEN** an XHTML document contains `<strong>`, `<em>`, `<code>`, `<br>` elements
- **THEN** strong becomes `**bold**`, emphasis becomes `*italic*`, inline code becomes `` `code` ``, and breaks become newlines

### Requirement: Broken EPUB repair
Scans local ZIP file headers when the central directory is missing or corrupt.

#### Scenario: Repairs EPUB with missing central directory
- **WHEN** an EPUB file fails to parse due to a missing or corrupt ZIP central directory
- **THEN** the tool scans each local file header in the ZIP to reconstruct the file listing
- **AND** extracts files based on local header information

#### Scenario: Logs repair warning
- **WHEN** central directory recovery is performed
- **THEN** a warning is logged indicating the EPUB had a corrupt central directory
- **AND** the recovery method is noted in the log
