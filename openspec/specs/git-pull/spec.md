# Git Pull

## ADDED Requirements

### Requirement: Single pull
`git_pull()` runs `git pull` in a project directory.

#### Scenario: Pull in specified directory
- **WHEN** `git_pull("/path/to/project")` is called
- **THEN** it runs `git pull` as a subprocess in the specified directory

### Requirement: Named pull
`git_pull_by_name()` looks up a project in zxtool.toml and pulls or clones.

#### Scenario: Pull by project name
- **WHEN** `git_pull_by_name("myproject")` is called and the project exists with a `dir` in zxtool.toml
- **THEN** it runs `git pull` in the project's directory

### Requirement: Bulk pull
`git_pull_all_projects()` iterates all projects in the config.

#### Scenario: Pull all projects
- **WHEN** `git_pull_all_projects()` is called
- **THEN** it iterates through all `[[projects]]` entries in zxtool.toml and runs `git_pull_by_name()` for each

### Requirement: Auto-clone
If the project directory is missing but `git_repository` is configured, runs `git clone`.

#### Scenario: Clone when directory is missing
- **WHEN** `git_pull_by_name("myproject")` is called and the project's `dir` does not exist but `git_repository` is configured in zxtool.toml
- **THEN** it runs `git clone <repository_url> <dir>` instead of `git pull`

### Requirement: Error handling
Timeout detection (120s for pull, 300s for clone), and missing git detection.

#### Scenario: Pull timeout
- **WHEN** a `git pull` subprocess exceeds 120 seconds
- **THEN** the process is terminated and an error is reported

#### Scenario: Clone timeout
- **WHEN** a `git clone` subprocess exceeds 300 seconds
- **THEN** the process is terminated and an error is reported

#### Scenario: Missing git executable
- **WHEN** `git` is not installed or not on the system PATH
- **THEN** a clear error message is returned indicating git is missing
