# Git Config

## ADDED Requirements

### Requirement: Config check
`check_git_config()` reads `user.name` and `user.email` from `.git/config`.

#### Scenario: Check reads local git config
- **WHEN** `check_git_config()` is called in a git repository
- **THEN** it reads `user.name` and `user.email` from the repository's `.git/config` file and returns them

#### Scenario: Check returns empty values outside repo
- **WHEN** `check_git_config()` is called outside a git repository
- **THEN** it returns empty or `None` values for `user.name` and `user.email`

### Requirement: Config fill
`fill_git_config()` writes user info with priority: CLI args > zxtool.toml > interactive input.

#### Scenario: Fill with CLI args takes priority
- **WHEN** `fill_git_config()` is called with explicit `name` and `email` arguments
- **THEN** those values are written to `.git/config` regardless of any values in zxtool.toml

#### Scenario: Fill falls back to zxtool.toml
- **WHEN** `fill_git_config()` is called without CLI args and matching `[[git.user]]` entries exist in zxtool.toml
- **THEN** the matching config values are used

#### Scenario: Fill falls back to interactive input
- **WHEN** `fill_git_config()` is called without CLI args and no matching config entry exists
- **THEN** the user is prompted interactively for name and email

### Requirement: Git dir discovery
`find_git_dir()` walks up from `start_path` looking for `.git`.

#### Scenario: Find git dir from subdirectory
- **WHEN** `find_git_dir("/a/b/c")` is called and `/a/b/.git` exists
- **THEN** it returns `Path("/a/b/.git")` by walking up the directory tree

#### Scenario: No git dir found
- **WHEN** `find_git_dir("/a/b/c")` is called and no `.git` directory exists in any parent
- **THEN** it returns `None`

### Requirement: Config file write
Uses `configparser` to read/write `.git/config`.

#### Scenario: Write user section to git config
- **WHEN** `fill_git_config()` determines the values to write
- **THEN** it uses `configparser` to write or update the `[user]` section in the repository's `.git/config` file with `name` and `email`
