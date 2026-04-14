# zxtoolbox

A collection of tools for frequently performed repetitive tasks on Windows, Mac, and Linux systems

<div align="center">

English | [Chinese](./README_zh.md)

</div>

## 0x01. Install

```shell
uv tool install zxtoolbox
```

## 0x02. Directory Structure
```text
toolbox/
├── doc/                    # Documentation directory
│   ├── index.md           # Project documentation
│   ├── computer_info.md   # Computer information retrieval documentation
│   ├── config_manager.md  # Configuration file management documentation
│   ├── git_config.md      # Git repository configuration documentation
│   ├── letsencrypt.md     # Let's Encrypt certificate documentation
│   ├── mkdocs_manager.md  # MkDocs project management documentation
│   ├── ssl_cert.md        # SSL certificate generation documentation
│   └── video_download.md  # Video download documentation
├── src/                   # Source code directory
│   └── zxtoolbox/         # Main package
│       ├── __init__.py    # Package initialization
│       ├── cli.py         # Command-line entry point
│       ├── computer_info.py    # Computer information retrieval
│       ├── config_manager.py   # Configuration file management
│       ├── git_config.py       # Git repository configuration management
│       ├── letsencrypt.py      # Let's Encrypt certificate management
│       ├── mkdocs_manager.py   # MkDocs project management
│       ├── pyopt_2fa.py        # 2FA tool
│       ├── ssl_cert.py         # SSL certificate generation
│       ├── video_download.py   # Video download
│       └── test/          # Test directory
├── pyproject.toml        # Project configuration and dependencies
├── README.md             # Project description
└── uv.lock               # uv locked dependency versions
```

## 0x03. Dependencies

### Core Dependencies

| Package | Purpose | Website |
|---------|---------|---------|
| paramiko | SSH connections | [paramiko.org](https://www.paramiko.org/) |
| prettytable | Table formatting | [github.com](https://github.com/jazzband/prettytable) |
| psutil | System information | [psutil.readthedocs.io](https://psutil.readthedocs.io/) |
| py-cpuinfo | CPU information | [github.com](https://github.com/workhorsy/py-cpuinfo) |
| nvidia-ml-py | NVIDIA GPU information | [github.com](https://github.com/NVIDIA/nvidia-ml-py) |
| pyotp | 2FA one-time passwords | [github.com](https://github.com/pyauth/pyotp) |
| yt-dlp | Video downloading | [github.com](https://github.com/yt-dlp/yt-dlp) |
| pyyaml | YAML parsing | [pyyaml.org](https://pyyaml.org/) |
| acme | ACME protocol (Let's Encrypt) | [github.com](https://github.com/certbot/certbot) |
| cryptography | Cryptographic functions | [cryptography.io](https://cryptography.io/) |
| requests | HTTP requests | [requests.readthedocs.io](https://requests.readthedocs.io/) |
| mkdocs | Documentation site building | [mkdocs.org](https://www.mkdocs.org/) |
| mkdocs-smzhbook-theme | MkDocs theme | [github.com](https://github.com/smallzh/mkdocs-smzhbook-theme) |

## 0x04. Running Unit Tests

The project uses `pytest` as the testing framework. Test files are located in the `src/zxtoolbox/test/` directory.

### Install Test Dependencies

```shell
uv add --dev pytest
```

### Run All Tests

```shell
uv run pytest src/zxtoolbox/test/ -v
```

### Run Single Test File

```shell
uv run pytest src/zxtoolbox/test/test_cli.py -v
```

### Run Specific Test Class or Method

```shell
# Run specific test class
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit -v

# Run specific test method
uv run pytest src/zxtoolbox/test/test_cli.py::TestCliGit::test_git_config_check -v
```

### View Test Coverage

```shell
uv add --dev pytest-cov
uv run pytest src/zxtoolbox/test/ --cov=zxtoolbox --cov-report=term-missing
```
