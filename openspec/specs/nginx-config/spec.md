## ADDED Requirements

### Requirement: Check
`check_nginx()` detects whether nginx is installed, identifies the config directory, and reports the current status.

#### Scenario: Detects nginx installation
- **WHEN** `check_nginx()` is called
- **THEN** it checks for the `nginx` binary on the system PATH
- **AND** reports whether nginx is installed and its version

#### Scenario: Identifies config directories
- **WHEN** `check_nginx()` is called
- **THEN** it detects the nginx config directory (typically `/etc/nginx` on Linux)
- **AND** checks for the existence of `sites-available/`, `sites-enabled/`, and `conf.d/` directories

#### Scenario: Reports site status
- **WHEN** `check_nginx()` runs successfully
- **THEN** it lists all sites in `sites-available/` and indicates which are enabled via `sites-enabled/` symlinks

### Requirement: Config generation
`generate_site_config()` produces a complete nginx site configuration file for HTTPS or HTTP-only serving.

#### Scenario: Generates full HTTPS config
- **WHEN** `generate_site_config()` is called with a domain name and SSL certificate paths
- **THEN** it produces a complete HTTPS server block with:
  - SSL certificate and key paths
  - Strong TLS protocols and ciphers
  - HTTP-to-HTTPS redirect server block
  - Root directory, server name, and recommended security headers

#### Scenario: Generates HTTP-only config
- **WHEN** `generate_site_config()` is called without SSL certificate paths
- **THEN** it produces an HTTP-only server block without any TLS directives

#### Scenario: Config includes proxy and static file settings
- **WHEN** `generate_site_config()` is called
- **THEN** the generated config supports specifying either a proxy pass target or a static root directory

### Requirement: Batch generation
`generate_from_config()` processes all domain projects defined in the TOML config and generates nginx site configs for each.

#### Scenario: Generates configs for all domain projects
- **WHEN** `generate_from_config()` is called
- **THEN** it reads all project entries from the config that have domain information
- **AND** calls `generate_site_config()` for each project

#### Scenario: Skips projects without required fields
- **WHEN** a project entry in the config is missing required fields (e.g., domain or root directory)
- **THEN** that project is skipped with a warning message

### Requirement: SSL auto-detection
Auto-resolves Let's Encrypt certificate paths for domains when SSL is requested.

#### Scenario: Resolves LE cert paths from config
- **WHEN** generating an HTTPS site config
- **THEN** it checks for Let's Encrypt certificate paths in the TOML config for the domain
- **AND** uses the resolved cert, fullchain, and privkey paths in the generated config

#### Scenario: Falls back to config-provided paths
- **WHEN** no LE config entry exists for the domain but SSL paths are manually provided
- **THEN** it uses the manually specified certificate and key paths

### Requirement: Enable/disable
`enable_site()` and `disable_site()` manage the `sites-available` to `sites-enabled` symlink lifecycle.

#### Scenario: Enable creates symlink
- **WHEN** `enable_site()` is called with a site name
- **THEN** it creates a symlink from `sites-available/<site>` to `sites-enabled/<site>`

#### Scenario: Disable removes symlink
- **WHEN** `disable_site()` is called with a site name
- **THEN** it removes the symlink from `sites-enabled/<site>` if it exists

#### Scenario: Enable errors for non-existent config
- **WHEN** `enable_site()` is called for a site that has no config file in `sites-available/`
- **THEN** an error is raised indicating the config file does not exist

### Requirement: Reload
`reload_nginx()` sends a reload signal to the nginx process.

#### Scenario: Reloads nginx successfully
- **WHEN** `reload_nginx()` is called
- **THEN** it executes `nginx -s reload` to apply configuration changes

#### Scenario: Tests config before reload
- **WHEN** `reload_nginx()` is called
- **THEN** it first runs `nginx -t` to validate the configuration syntax
- **AND** only reloads if the test passes
- **AND** reports the test output if the configuration is invalid
