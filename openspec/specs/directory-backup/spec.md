## ADDED Requirements

### Requirement: Directory copy
Copies source directory contents to a target directory recursively, preserving the directory structure.

#### Scenario: Copies all files recursively
- **WHEN** `copy_directory()` is called with a source path and a target path
- **THEN** all files and subdirectories from the source are copied to the target
- **AND** the directory structure is preserved

#### Scenario: Overwrites existing files
- **WHEN** a file in the target already exists with the same name
- **THEN** it is overwritten by the source file

#### Scenario: Source must be a directory
- **WHEN** the source path is not a directory or does not exist
- **THEN** an error is raised indicating the source is invalid

### Requirement: Git awareness
If the target directory is a git repository, changes are committed; otherwise a timestamped backup directory is created.

#### Scenario: Commits changes in git repo
- **WHEN** the target directory is a git repository with changes
- **THEN** all copied files are staged via `git add`
- **AND** a commit is created with a descriptive message

#### Scenario: Creates backup directory for non-git targets
- **WHEN** the target directory is not a git repository
- **THEN** the source contents are copied into a timestamped subdirectory within the target (e.g., `target/backup-2025-01-15-143022/`)

#### Scenario: Detects git repo status
- **WHEN** checking if the target is a git repo
- **THEN** it checks for the existence of a `.git` directory in the target path
- **AND** verifies it is a valid git repository

### Requirement: File backup
For non-git targets, overwritten files are backed up to a `.zxtool_backups/` directory with a timestamp before being replaced.

#### Scenario: Backs up overwritten files
- **WHEN** a file in the target directory is about to be overwritten (non-git target)
- **THEN** the existing file is first copied to `.zxtool_backups/<original-path>/<timestamp>_<filename>`

#### Scenario: Preserves original directory structure in backup
- **WHEN** a file is backed up from a subdirectory
- **THEN** the relative path structure is maintained within `.zxtool_backups/`

### Requirement: Backup log
Generates or updates a `backup-records.md` file in the backup directory with details about each backup operation.

#### Scenario: Creates backup log on first backup
- **WHEN** a backup operation completes
- **THEN** a `backup-records.md` file is created in the target directory

#### Scenario: Records backup metadata
- **WHEN** `backup-records.md` is generated or updated
- **THEN** it contains:
  - Timestamp of the backup
  - Source directory path
  - Number of files copied
  - Total size of copied data
  - List of overwritten files (if any)

#### Scenario: Appends to existing log
- **WHEN** a subsequent backup operation runs in the same target directory
- **THEN** new backup entries are appended to the existing `backup-records.md`

### Requirement: Custom commit message
Accepts a custom commit message when committing to a git target.

#### Scenario: Uses custom commit message
- **WHEN** `copy_directory()` is called with `--message "Custom message"` and the target is a git repo
- **THEN** the git commit uses the provided custom message

#### Scenario: Falls back to default message
- **WHEN** no custom message is provided
- **THEN** the commit message defaults to something descriptive (e.g., "Backup from <source> on <date>")
