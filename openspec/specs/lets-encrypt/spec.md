## ADDED Requirements

### Requirement: acme.sh management
`AcmeShManager` provides methods to install, check version, and execute acme.sh commands.

#### Scenario: Installs acme.sh
- **WHEN** `AcmeShManager.install()` is called
- **THEN** it downloads and runs the acme.sh installer script from `get.acme.sh`
- **AND** sets up the acme.sh environment in `~/.acme.sh/`

#### Scenario: Checks acme.sh version
- **WHEN** `AcmeShManager.version()` is called
- **THEN** it runs `acme.sh --version` and parses the output
- **AND** returns the installed version string

#### Scenario: Executes acme.sh commands
- **WHEN** `AcmeShManager.execute()` is called with a list of arguments
- **THEN** it runs `acme.sh` as a subprocess with the given arguments
- **AND** returns the stdout, stderr, and exit code

### Requirement: Certificate issuance
Supports DNS-01 challenge (manual mode, Cloudflare API, Aliyun API) and HTTP-01 challenge (webroot, standalone mode).

#### Scenario: Issues cert via DNS-01 manual mode
- **WHEN** issuing a certificate with `--dns dns_manual`
- **THEN** acme.sh prints the required DNS TXT record
- **AND** waits for the user to confirm the DNS record has been added

#### Scenario: Issues cert via Cloudflare DNS API
- **WHEN** issuing with `--dns dns_cf` and CF_Token / CF_Zone_ID are set
- **THEN** acme.sh automatically creates and removes the DNS TXT record via Cloudflare API

#### Scenario: Issues cert via HTTP-01 webroot
- **WHEN** issuing with `--webroot /path/to/webroot`
- **THEN** acme.sh writes the challenge file to the specified webroot
- **AND** Let's Encrypt validates the challenge via HTTP request

#### Scenario: Issues cert via HTTP-01 standalone
- **WHEN** issuing with `--standalone`
- **THEN** acme.sh starts a temporary web server on port 80 to respond to the HTTP challenge

#### Scenario: Wildcard certificates require DNS-01
- **WHEN** issuing a wildcard certificate (e.g., `*.example.com`)
- **THEN** the issuance uses DNS-01 challenge type
- **AND** HTTP-01 is rejected with an error since wildcard domains require DNS validation

### Requirement: Certificate renewal
Auto-detects certificate expiration and renews certificates within a 30-day window before expiry.

#### Scenario: Renews cert within 30-day window
- **WHEN** `renew()` is called for a domain whose certificate expires within 30 days
- **THEN** the certificate is renewed via acme.sh `--renew`

#### Scenario: Skips renewal for non-expiring certs
- **WHEN** `renew()` is called for a domain whose certificate expires more than 30 days in the future
- **THEN** the certificate is not renewed
- **AND** a message is printed indicating the cert is still valid

#### Scenario: Force renew skips expiry check
- **WHEN** `renew()` is called with `--force`
- **THEN** the certificate is renewed regardless of the expiration date

### Requirement: Batch operations
`batch_obtain_certs()` processes all domain projects from the TOML config and issues/renews certificates for each.

#### Scenario: Issues certs for all domain projects
- **WHEN** `batch_obtain_certs()` is called
- **THEN** it reads all domain projects from the config's `[letsencrypt]` section
- **AND** issues or renews certificates for each domain

#### Scenario: Skips projects with no domains
- **WHEN** a project in the batch list has no domain configured
- **THEN** it is skipped with a warning message

#### Scenario: Dry-run previews without issuing
- **WHEN** `batch_obtain_certs()` is called with `--dry-run`
- **THEN** it lists the projects and domains that would be processed
- **AND** does not execute any actual acme.sh commands

### Requirement: Certificate status
Shows expiration dates and health status for managed certificates.

#### Scenario: Displays certificate details
- **WHEN** `status()` is called for a domain
- **THEN** it reads the certificate file and displays:
  - Subject and issuer
  - Issuance and expiration dates
  - SAN list
  - Days remaining until expiry

#### Scenario: Shows health status
- **WHEN** `status()` displays certificate information
- **THEN** each certificate is marked with a health status:
  - `VALID` if more than 30 days remaining
  - `EXPIRING_SOON` if 30 or fewer days remaining
  - `EXPIRED` if past expiration date

### Requirement: Cron management
Installs and uninstalls system cron jobs for automatic certificate renewal.

#### Scenario: Installs auto-renew cron
- **WHEN** `cron_install()` is called
- **THEN** it adds a cron job that runs `acme.sh --cron` daily (or at a configured interval)

#### Scenario: Uninstalls auto-renew cron
- **WHEN** `cron_uninstall()` is called
- **THEN** it removes the previously installed acme.sh cron job

#### Scenario: Shows current cron status
- **WHEN** `cron_status()` is called
- **THEN** it checks whether the acme.sh cron job is currently installed
- **AND** prints the cron schedule if present

### Requirement: Revocation
Revoke certificates and update the state file to mark them as revoked.

#### Scenario: Revokes a certificate
- **WHEN** `revoke()` is called with a domain name
- **THEN** it runs `acme.sh --revoke` for the domain's certificate
- **AND** confirms the revocation with the CA

#### Scenario: Updates state after revocation
- **WHEN** revocation completes successfully
- **THEN** the local state file is updated to record the certificate as revoked
- **AND** subsequent status checks show the certificate as `REVOKED`
