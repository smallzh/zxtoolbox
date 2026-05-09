# CLI Dispatch

## ADDED Requirements

### Requirement: CLI entry point
The `zxtool` entry point dispatches to subcommands via argparse.

#### Scenario: Main entry point dispatches subcommand
- **WHEN** a user runs `zxtool <subcommand> [args]` from the shell
- **THEN** the `main()` function in `cli.py` parses arguments via argparse and dispatches to the corresponding `handle_*()` function

### Requirement: Subcommand registration
Each subcommand has a `_build_*_parser()` and `handle_*()` function.

#### Scenario: Subcommand parser and handler pair
- **WHEN** a new subcommand is added to the CLI
- **THEN** it must define a `_build_*_parser(subparsers)` function to register its arguments and a `handle_*(args)` function for dispatch logic

### Requirement: Version output
`-v`/`--version` outputs package version from importlib.metadata.

#### Scenario: Version flag displays version
- **WHEN** a user runs `zxtool -v` or `zxtool --version`
- **THEN** the CLI outputs the package version string retrieved via `importlib.metadata.version("zxtoolbox")` and exits

### Requirement: Help auto-generation
argparse generates help text for each parser level.

#### Scenario: Help flag displays usage
- **WHEN** a user runs `zxtool --help`, `zxtool <subcommand> --help`, or `zxtool <subcommand> <subsubcommand> --help`
- **THEN** argparse prints the auto-generated help text for that parser level showing available subcommands and arguments

### Requirement: Subcommand enumeration
14 top-level subcommands are registered (ci, totp, video, http, ssl, mkdocs, nginx, config, git, epub, backup, mkpdf, le, feishu).

#### Scenario: All subcommands are registered
- **WHEN** a user runs `zxtool --help`
- **THEN** the help output lists exactly 14 top-level subcommands: ci, totp, video, http, ssl, mkdocs, nginx, config, git, epub, backup, mkpdf, le, feishu
