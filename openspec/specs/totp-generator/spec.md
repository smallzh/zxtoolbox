## ADDED Requirements

### Requirement: TOTP code generation
Generates a time-based one-time password (TOTP) from a provided secret key, following the RFC 6238 algorithm.

#### Scenario: Generates TOTP from base32 secret
- **WHEN** `generate_totp()` is called with a Base32-encoded secret key
- **THEN** a 6-digit TOTP code is computed using the current Unix timestamp
- **AND** the code is returned as a string

#### Scenario: Uses standard TOTP parameters
- **WHEN** generating the TOTP code
- **THEN** the algorithm uses 30-second time step and 6-digit output length as specified in RFC 6238

#### Scenario: Errors on invalid secret
- **WHEN** the provided secret key is not valid Base32
- **THEN** an error is raised indicating the secret is invalid

### Requirement: Current time code
Outputs the TOTP code valid for the current 30-second window.

#### Scenario: Outputs code for current time window
- **WHEN** `generate_totp()` is called
- **THEN** the generated code is valid for the current 30-second TOTP window

#### Scenario: Output includes remaining seconds
- **WHEN** the TOTP code is displayed
- **THEN** the remaining seconds in the current time window are shown alongside the code
