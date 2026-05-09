# Config Management

## ADDED Requirements

### Requirement: Config file location
The default config file is located at `~/.config/zxtool.toml`.

#### Scenario: Default config path resolution
- **WHEN** `load_config()` is called without a `config_path` argument
- **THEN** it resolves the config file from `~/.config/zxtool.toml` using `Path.home()`

### Requirement: TOML parsing
Uses `tomllib` for reading and `generate_config_content()` for writing.

#### Scenario: Read config file
- **WHEN** `load_config()` reads an existing TOML file
- **THEN** it uses `tomllib.load()` to parse the file and returns the parsed dictionary

#### Scenario: Write config file
- **WHEN** `generate_config_content()` is called with configuration data
- **THEN** it produces a TOML-formatted string suitable for writing to the config file

### Requirement: Config sections
Supports `[letsencrypt]`, `[nginx]`, `[logging]`, `[feishu]`, `[[projects]]`, and `[[git.user]]` sections.

#### Scenario: Sub-config loaders extract specific sections
- **WHEN** `load_le_config()`, `load_nginx_config()`, `load_logging_config()`, or `load_feishu_config()` is called
- **THEN** they extract and return the corresponding section from the parsed config dict

#### Scenario: Array-of-tables sections supported
- **WHEN** the config file contains `[[projects]]` or `[[git.user]]` entries
- **THEN** they are parsed as lists of tables and accessible via `load_project_by_name()` and related functions

### Requirement: Interactive init
`zxtool config init` walks through all sections via CLI prompts.

#### Scenario: Config init walks through all sections
- **WHEN** a user runs `zxtool config init`
- **THEN** the CLI walks through each config section interactively, prompting for values with sensible defaults, and writes the resulting file to `~/.config/zxtool.toml`

### Requirement: Project lookup
`load_project_by_name()` and `load_projects_with_domain()` support project-level queries.

#### Scenario: Load project by name
- **WHEN** `load_project_by_name("project_name")` is called
- **THEN** it returns the matching project dict from `[[projects]]` or `None` if not found

#### Scenario: Load projects by domain
- **WHEN** `load_projects_with_domain("example.com")` is called
- **THEN** it returns a list of project dicts whose `domain` field matches the given domain

### Requirement: Config override
All module functions accept a `config_path` parameter to override the default config location.

#### Scenario: Custom config path passed to function
- **WHEN** any module-level function that reads config is called with a `config_path` argument
- **THEN** it passes that path to `load_config()` instead of using the default `~/.config/zxtool.toml`
