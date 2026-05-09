## ADDED Requirements

### Requirement: Project creation
`create_project()` generates the mkdocs.yml configuration file and docs/index.md starter page for a new MkDocs project.

#### Scenario: Creates mkdocs.yml with default configuration
- **WHEN** `create_project()` is called with a project name and directory
- **THEN** it creates `mkdocs.yml` containing site name, theme, and nav sections
- **AND** it creates `docs/index.md` with a top-level heading matching the project name

#### Scenario: Does not overwrite existing project
- **WHEN** `create_project()` is called for a directory that already contains `mkdocs.yml`
- **THEN** the function returns early without modifying existing files

### Requirement: Single build
`build_project()` runs `python -m mkdocs build` with configurable config file path and output directory.

#### Scenario: Builds with default config
- **WHEN** `build_project()` is called with a project directory
- **THEN** it executes `mkdocs build` in that directory using the default `mkdocs.yml`

#### Scenario: Builds with custom config and output
- **WHEN** `build_project()` is called with a custom `--config` file path and `--output` directory
- **THEN** it passes the `-f` and `-d` flags to `mkdocs build`

### Requirement: Named build
`build_project_by_name()` looks up a project from the TOML config and delegates to `build_project()`.

#### Scenario: Builds project by name from config
- **WHEN** `build_project_by_name()` is called with a project name that exists in the TOML config
- **THEN** it loads the project's path and settings from the config
- **AND** it calls `build_project()` with the resolved path and options

#### Scenario: Errors on unknown project name
- **WHEN** `build_project_by_name()` is called with a project name not found in the TOML config
- **THEN** it raises a `KeyError` or exits with a clear error message listing available projects

### Requirement: Batch build
`batch_build()` processes multiple projects from the TOML config sequentially.

#### Scenario: Builds all projects from config
- **WHEN** `batch_build()` is called without a project filter
- **THEN** it iterates over all projects defined in the `[mkdocs]` section of the config
- **AND** it calls `build_project_by_name()` for each project

#### Scenario: Builds selected projects only
- **WHEN** `batch_build()` is called with a list of specific project names
- **THEN** it builds only those named projects

#### Scenario: Handles build failure without aborting
- **WHEN** one project in a batch build fails
- **THEN** the error is logged
- **AND** the function continues building the remaining projects

### Requirement: Dev server
`serve_project()` runs `mkdocs serve` with a configurable address and port.

#### Scenario: Serves with default address
- **WHEN** `serve_project()` is called with a project directory
- **THEN** it runs `mkdocs serve` bound to `127.0.0.1:8000` by default

#### Scenario: Serves with custom address and port
- **WHEN** `serve_project()` is called with `--address 0.0.0.0:9000`
- **THEN** it passes `-a 0.0.0.0:9000` to `mkdocs serve`

### Requirement: Dry-run support
Batch operations support `--dry-run` flag to preview what would be built without executing.

#### Scenario: Dry-run lists projects without building
- **WHEN** `batch_build()` is called with `--dry-run`
- **THEN** it prints each project name and its source directory
- **AND** it does not execute `mkdocs build` for any project

#### Scenario: Dry-run message format
- **WHEN** `--dry-run` is active
- **THEN** each line is prefixed with `[DRY-RUN]` to clearly indicate no action was taken
