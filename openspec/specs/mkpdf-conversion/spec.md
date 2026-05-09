## ADDED Requirements

### Requirement: Markdown to PDF
Converts a single Markdown file or all Markdown files in a directory to PDF via browser print-to-PDF.

#### Scenario: Converts a single .md file to PDF
- **WHEN** `convert()` is called with a path to a single `.md` file
- **THEN** it renders the Markdown as HTML in the browser
- **AND** triggers browser print-to-PDF
- **AND** saves the output as a `.pdf` file alongside the source

#### Scenario: Converts all .md files in a directory
- **WHEN** `convert()` is called with a directory path
- **THEN** it finds all `.md` files recursively in that directory
- **AND** converts each file to PDF individually

#### Scenario: Output path respects custom destination
- **WHEN** `convert()` is called with `--output` flag
- **THEN** the resulting PDF is saved to the specified output path instead of the default location

### Requirement: Browser discovery
Auto-detects Edge, Chrome, or Chromium installed on the system, prioritized by platform.

#### Scenario: Finds Edge on Windows
- **WHEN** running on Windows
- **THEN** the browser discovery checks the Edge installation path first (`%PROGRAMFILES%\\Microsoft\\Edge\\Application\\msedge.exe`)

#### Scenario: Finds Chrome on macOS
- **WHEN** running on macOS
- **THEN** the browser discovery checks `/Applications/Google Chrome.app/.../Google Chrome` first

#### Scenario: Falls back through browser candidates
- **WHEN** the preferred browser is not found
- **THEN** it iterates through a list of known browser paths for the current platform
- **AND** uses the first one found

#### Scenario: Errors when no browser is found
- **WHEN** no supported browser is detected on the system
- **THEN** a clear error message is shown listing the browsers that were searched for

### Requirement: Mermaid support
Renders fenced code blocks tagged with `mermaid` using a bundled `mermaid.min.js` JavaScript file.

#### Scenario: Renders mermaid diagrams via bundled JS
- **WHEN** the Markdown contains a ```mermaid code block
- **THEN** the generated HTML includes a `<div class="mermaid">` element with the diagram source
- **AND** the HTML references a locally bundled `mermaid.min.js` (no CDN dependency)

#### Scenario: Mermaid render wait time is configurable
- **WHEN** the page contains Mermaid diagrams
- **THEN** the tool waits for Mermaid rendering to complete before triggering PDF print
- **AND** the wait duration is determined by the configurable render wait time setting

### Requirement: Document title
Extracts the document title from YAML front matter `title` field or the first `#` heading in the Markdown.

#### Scenario: Extracts title from front matter
- **WHEN** the Markdown file has a YAML front matter block with a `title:` field
- **THEN** the extracted title is used as the PDF document title and the HTML page title

#### Scenario: Falls back to first heading
- **WHEN** the Markdown file has no front matter or no `title` in front matter
- **THEN** the first `# Heading` found in the document body is used as the title

#### Scenario: Falls back to filename
- **WHEN** there is no front matter title and no heading found
- **THEN** the filename (without extension) is used as the title

### Requirement: HTML output
Renders Markdown as styled HTML before sending it to the browser for PDF conversion.

#### Scenario: Renders Markdown to styled HTML
- **WHEN** Markdown content is processed
- **THEN** it is converted to HTML using a Markdown-to-HTML renderer
- **AND** the HTML is wrapped in a styled template with CSS for print formatting

#### Scenario: Includes syntax highlighting in HTML
- **WHEN** the Markdown contains fenced code blocks with language tags
- **THEN** the generated HTML includes syntax-highlighted code via a bundled highlighting library

### Requirement: Render wait
Configurable render wait time (default 5000ms) to allow JavaScript rendering (Mermaid, etc.) to complete before the PDF is generated.

#### Scenario: Uses default wait time
- **WHEN** no custom render wait time is specified
- **THEN** the tool waits 5000ms after page load before triggering PDF print

#### Scenario: Respects custom wait time
- **WHEN** a custom `--wait` or render wait option is provided (e.g., `--wait 8000`)
- **THEN** the tool waits the specified number of milliseconds before printing to PDF

### Requirement: Front matter stripping
Strips YAML front matter (delimited by `---`) from the Markdown before rendering to HTML.

#### Scenario: Strips front matter before rendering
- **WHEN** the Markdown file begins with a YAML front matter block between `---` delimiters
- **THEN** the front matter is parsed and removed from the Markdown body before HTML conversion
- **AND** metadata fields (e.g., `title`) are preserved for document-level use

#### Scenario: Handles files without front matter
- **WHEN** the Markdown file does not contain any YAML front matter
- **THEN** the content is processed normally without any stripping
