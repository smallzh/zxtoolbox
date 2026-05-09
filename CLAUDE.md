# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install/sync dependencies
uv sync

# Run CLI
uv run zxtool --help
uv run zxtool <command> [subcommand] [options]

# Run all tests
uv run pytest src/zxtoolbox/test/ -v

# Run single test file
uv run pytest src/zxtoolbox/test/test_cli.py -v

# Run specific test class or method
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit -v
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit::test_git_config_check -v

# Build distribution
uv build

# Serve docs locally
uv run mkdocs serve
```

## Project Overview

**zxtoolbox** is a cross-platform (Windows/Mac/Linux) Python CLI tool collection that wraps repetitive tasks. The CLI entry point is `zxtool`, installed via `uv tool install zxtoolbox`.

- Python >= 3.13, package management via **uv**, build system **uv_build**
- Main dependency: `pyproject.toml` at repo root
- Config file: `~/.config/zxtool.toml` (TOML format)

## Architecture

### CLI dispatcher pattern (`src/zxtoolbox/cli.py`)

The `main()` function builds an `argparse` parser with subcommands, then dispatches to handler functions. Each subcommand's arguments are defined in a `_build_*_parser()` function, and dispatch logic lives in a `handle_*()` function. The handler functions directly call module-level functions from each feature module.

### Module layout

```
src/zxtoolbox/
├── __init__.py          # Package metadata (version from importlib)
├── cli.py               # CLI parser + dispatch (orchestrator)
├── config_manager.py    # TOML config at ~/.config/zxtool.toml
├── logging_manager.py   # Logging setup (called once at startup)
├── computer_info.py     # CPU/memory/disk/GPU info (PrettyTable)
├── git_config.py        # Git user config check/fill, git pull
├── mkdocs_manager.py    # MkDocs project create/build/batch/serve
├── mkpdf_manager.py     # Markdown-to-PDF via browser print
├── ssl_cert.py          # Self-signed SSL cert generation
├── letsencrypt.py       # Let's Encrypt ACME v2 certs (acme.sh)
├── nginx_manager.py     # Nginx site config generation
├── feishu_client.py     # Feishu (Lark) bot via WebSocket
├── video_download.py    # yt-dlp video download
├── pyopt_2fa.py         # TOTP code generation
├── epub_manager.py      # EPUB to Markdown conversion
├── backup_manager.py    # Directory copy with backup/git commit
├── http_server.py       # Static file HTTP server
└── test/
    ├── __init__.py
    ├── test_cli.py           # Tests all CLI subcommands via mock
    ├── test_backup_manager.py
    ├── test_computer_info.py
    ├── test_config_manager.py
    ├── test_epub_manager.py
    ├── test_git_config.py
    ├── test_http_server.py
    ├── test_letsencrypt.py
    ├── test_logging_manager.py
    ├── test_mkdocs_manager.py
    ├── test_mkpdf_manager.py
    ├── test_nginx_manager.py
    ├── test_pyopt_2fa.py
    ├── test_ssl_cert.py
    ├── test_video_download.py
```

### Key patterns

1. **Config-driven workflows**: `config_manager.py` reads `~/.config/zxtool.toml` (TOML). `load_config()` returns a dict. Sub-config loaders (`load_le_config`, `load_nginx_config`, etc.) extract specific sections. `load_project_by_name()` and `load_projects_with_domain()` support project-level lookups. The config drives batch operations for MkDocs, Let's Encrypt, Nginx, and Git.

2. **Each module is self-contained**: Feature modules import only standard library + direct dependencies. They do not import from each other (except `config_manager.py` which is used by many modules). CLI dispatch in `cli.py` is the only place that wires features together.

3. **Testing uses mocking heavily**: Tests in `test_cli.py` mock `logging_manager.setup_logging()` and each feature module's functions, then verify correct argument passing via `assert_called_once_with`. Other test files (e.g., `test_backup_manager.py`) test actual module logic with temp directories and real file operations.

### CLI commands

| Command | Subcommands | Description |
|---------|-------------|-------------|
| `ci` | — | Show computer info (summary or `--all`) |
| `totp` | — | Generate TOTP code from key |
| `video` | — | Download video via yt-dlp |
| `http` | `serve` | Static file HTTP server |
| `ssl` | `init`, `root`, `cert` | Self-signed SSL cert management |
| `mkdocs` | `create`, `build`, `batch`, `serve` | MkDocs project management |
| `nginx` | `check`, `generate`, `enable`, `disable`, `reload` | Nginx config management |
| `config` | `init`, `show` | zxtool.toml config management |
| `git` | `config check`, `config fill`, `pull` | Git config and pull |
| `epub` | `convert` | EPUB to Markdown conversion |
| `backup` | `copy` | Directory copy with backup |
| `mkpdf` | — | Markdown to PDF (needs Edge/Chrome) |
| `le` | `issue`, `renew`, `batch`, `status`, `revoke`, `init`, `cron` | Let's Encrypt cert management |
| `feishu` | `start`, `check` | Feishu bot client |

### Notable details

- **mkpdf_manager.py** requires Edge, Chrome, or Chromium installed for headless PDF printing. Mermaid rendering uses a bundled JS file (no CDN dependency).
- **letsencrypt.py** wraps `acme.sh` as a subprocess for certificate operations.
- **logging_manager.py** is called once by `cli.py` at startup. Most test files use `@patch("zxtoolbox.logging_manager.setup_logging")` to suppress it.
- **feishu_client.py** uses lark-oapi WebSocket for real-time message events; commands received via chat can trigger `git pull` or `mkdocs batch`.
