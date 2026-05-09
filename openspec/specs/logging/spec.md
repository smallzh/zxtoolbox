# Logging

## ADDED Requirements

### Requirement: Single initialization
`setup_logging()` only runs once, guarded by an `_initialized` flag.

#### Scenario: Subsequent calls are no-ops
- **WHEN** `setup_logging()` is called more than once
- **THEN** the second and subsequent calls return immediately without reconfiguring handlers because the `_initialized` flag is already set

### Requirement: Daily rotation
Uses `TimedRotatingFileHandler` with midnight rollover.

#### Scenario: Log file rotates at midnight
- **WHEN** the system clock passes midnight
- **THEN** `TimedRotatingFileHandler` rotates the log file, renaming the previous day's log and starting a new file

### Requirement: 7-day retention
`backupCount=7` for log file cleanup.

#### Scenario: Old log files are cleaned up
- **WHEN** more than 7 rotated log files exist
- **THEN** the oldest log files beyond `backupCount=7` are automatically deleted by the handler

### Requirement: Config-driven
Reads `log_dir` and `log_level` from `~/.config/zxtool.toml`.

#### Scenario: Log directory from config
- **WHEN** `setup_logging()` reads the config and finds a `log_dir` value
- **THEN** log files are created in that directory

#### Scenario: Log level from config
- **WHEN** `setup_logging()` reads the config and finds a `log_level` value
- **THEN** the root logger level is set to the corresponding Python logging level

### Requirement: Graceful fallback
Silent failure if the log directory is unwritable.

#### Scenario: Unwritable log directory
- **WHEN** the configured `log_dir` does not exist or is not writable
- **THEN** `setup_logging()` fails silently without raising an exception, and logging falls back to default behavior

### Requirement: Test reset
`reset_logging()` clears handlers and resets `_initialized`.

#### Scenario: Reset allows re-initialization
- **WHEN** `reset_logging()` is called
- **THEN** all logging handlers are removed from the root logger and the `_initialized` flag is reset to `False`, allowing `setup_logging()` to run again on the next call
