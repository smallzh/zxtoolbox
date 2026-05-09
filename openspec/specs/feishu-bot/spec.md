# Feishu Bot

## ADDED Requirements

### Requirement: WebSocket connection
Connects to Feishu via lark-oapi WebSocket for real-time message events.

#### Scenario: WebSocket connection established
- **WHEN** the feishu bot starts
- **THEN** it establishes a WebSocket connection to Feishu using the lark-oapi SDK and listens for real-time message events

#### Scenario: Real-time message events received
- **WHEN** a chat message is sent to the bot
- **THEN** the WebSocket client receives the message event and processes it

### Requirement: Command execution
Supports `git pull` and `mkdocs batch` commands via chat messages.

#### Scenario: Git pull command from chat
- **WHEN** a user sends a chat message matching the `git pull` command pattern
- **THEN** the bot executes `git_pull_all_projects()` and replies with the result

#### Scenario: Mkdocs batch command from chat
- **WHEN** a user sends a chat message matching the `mkdocs batch` command pattern
- **THEN** the bot executes `mkdocs_batch_run()` and replies with the result

#### Scenario: Unknown command from chat
- **WHEN** a user sends a chat message that does not match any supported command
- **THEN** the bot replies with a help message listing available commands

### Requirement: Config-based auth
Reads `app_id`/`app_secret` from zxtool.toml or CLI arguments.

#### Scenario: Auth from config file
- **WHEN** the feishu bot starts and `[feishu]` section exists in zxtool.toml with `app_id` and `app_secret`
- **THEN** those values are used for authentication

#### Scenario: Auth from CLI arguments
- **WHEN** the feishu bot starts with `--app-id` and `--app-secret` CLI flags
- **THEN** those values override any config file values

### Requirement: Graceful startup
Validates config before connecting, reports missing credentials clearly.

#### Scenario: Missing credentials reported
- **WHEN** the feishu bot starts without `app_id` or `app_secret` configured in either config file or CLI arguments
- **THEN** it prints a clear error message indicating the missing credentials and exits without attempting to connect

#### Scenario: Invalid credentials handled
- **WHEN** the feishu bot starts with credentials but the Feishu API rejects them
- **THEN** it logs the authentication error and exits gracefully
