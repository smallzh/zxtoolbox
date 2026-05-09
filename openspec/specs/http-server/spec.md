## ADDED Requirements

### Requirement: Static file serving
Serves files from a specified directory via HTTP, mapping URL paths to the filesystem.

#### Scenario: Serves files over HTTP
- **WHEN** a client requests a URL path that maps to an existing file in the served directory
- **THEN** the server responds with the file content and the correct MIME type

#### Scenario: Returns directory listing for root
- **WHEN** a client requests the root URL (`/`)
- **THEN** the server returns a directory listing showing available files and subdirectories

#### Scenario: Returns 404 for missing files
- **WHEN** a client requests a URL path that does not correspond to any file
- **THEN** the server returns a 404 Not Found response

### Requirement: Configurable host/port
The server binds to a configurable host address and port, defaulting to `127.0.0.1:8000`.

#### Scenario: Binds to default address
- **WHEN** `serve()` is called with no host or port arguments
- **THEN** the server starts on `127.0.0.1:8000`

#### Scenario: Binds to custom host and port
- **WHEN** `serve()` is called with `--host 0.0.0.0 --port 8080`
- **THEN** the server starts on `0.0.0.0:8080`

### Requirement: Threaded server
Uses `ThreadingHTTPServer` (or `socketserver.ThreadingMixIn`) to handle concurrent requests.

#### Scenario: Handles concurrent requests
- **WHEN** multiple clients make simultaneous requests
- **THEN** each request is handled in a separate thread
- **AND** no request blocks another from being processed

### Requirement: Directory validation
Validates that the specified directory exists before starting the server.

#### Scenario: Validates directory exists
- **WHEN** `serve()` is called with a directory path
- **THEN** the path is checked for existence and that it is a directory

#### Scenario: Errors on non-existent directory
- **WHEN** the specified directory does not exist
- **THEN** an error is raised indicating the directory was not found
- **AND** the server is not started

#### Scenario: Errors on file path instead of directory
- **WHEN** the specified path points to a file rather than a directory
- **THEN** an error is raised indicating a directory is required
- **AND** the server is not started
